"""从自然语言中增量抽取规格信息。"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from ..messages import content_to_text
from ..timing import phase
from .schemas import LIST_FIELDS, ProjectSpecification, SpecificationPatch

_EXTRACTION_PROMPT = """\
你是需求规格抽取助手。请只从用户本轮输入中抽取新增或修正的信息。

规则：
1. 没有新信息的字段返回 null。
2. 列表字段只返回本轮新增的条目，不要重复已有条目。
3. 用户明确说“A 改成 B”“技术栈不要 X 了”等覆盖或删除语义时，
   使用 remove_items 删除旧条目，或使用 replace_lists 给出修改后的完整列表。
4. 不要编造用户没有提供的信息。
5. 只输出结构化结果，不要输出解释、Markdown 代码块或其他文字。

当前规格对象：
{current_spec}
"""

_SHORT_ACKNOWLEDGEMENTS = {
    "对",
    "对的",
    "好",
    "好的",
    "嗯",
    "嗯嗯",
    "可以",
    "行",
    "ok",
    "yes",
    "是的",
    "没错",
    "继续",
    "不用",
    "先这样",
}

_TECH_SEPARATORS = re.compile(r"[,，、;；]|(?:和|以及)")


def _split_list_items(text: str) -> list[str]:
    return [
        item.strip()
        for item in _TECH_SEPARATORS.split(text)
        if item.strip()
    ]


def _fast_extract_patch(user_input: str) -> SpecificationPatch | None:
    """对高确定性短输入做本地抽取，避免不必要的 utility LLM 调用。"""
    text = user_input.strip()
    if len(text) > 80:
        return None

    project_match = re.fullmatch(
        r"(?:项目|产品)(?:名称|名字)?(?:叫|命名为)\s*(.+?)\s*[。！？!?]?",
        text,
    ) or re.fullmatch(
        r"(?:项目名称|产品名称)(?:是|为)\s*(.+?)\s*[。！？!?]?",
        text,
    )
    if project_match and project_match.group(1):
        name = project_match.group(1).strip()
        if len(name) <= 30:
            return SpecificationPatch(project_name=name)

    tech_match = re.fullmatch(
        r"(?:技术栈|技术选型)(?:是|为|用|采用|使用)\s*(.+?)\s*[。！？!?]?",
        text,
    )
    if tech_match and tech_match.group(1):
        return SpecificationPatch(
            replace_lists={"tech_stack": _split_list_items(tech_match.group(1))}
        )

    build_with_match = re.fullmatch(
        r"用\s*(.+?)\s*(?:开发|实现|做|来写)\s*[。！？!?]?",
        text,
    )
    if build_with_match and build_with_match.group(1):
        return SpecificationPatch(
            tech_stack=_split_list_items(build_with_match.group(1))
        )

    return None


def should_extract_specification(user_input: str) -> bool:
    """跳过简单确认语，避免为无新增信息的回复调用 LLM。"""
    normalized = re.sub(r"[\s，。！？!?.,]+", "", user_input).lower()
    return normalized not in _SHORT_ACKNOWLEDGEMENTS


def _parse_json_content(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    if isinstance(content, BaseModel):
        return content.model_dump(exclude_none=True)

    text = content_to_text(content).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        candidate = match.group(0)
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        return json.loads(candidate)


def _merge_unique(current: list[str], incoming: list[str]) -> list[str]:
    merged = list(current)
    for item in incoming:
        if item not in merged:
            merged.append(item)
    return merged


def merge_specification(
    current: ProjectSpecification,
    patch: SpecificationPatch,
) -> ProjectSpecification:
    """把单轮增量信息合并到已有规格对象。"""
    data = current.model_dump()
    patch_data = patch.model_dump(exclude_none=True)

    operation_fields = {"remove_items", "replace_lists"}
    for field, value in patch_data.items():
        if field in operation_fields:
            continue
        if field in LIST_FIELDS:
            data[field] = _merge_unique(data[field], value or [])
        elif value is not None:
            data[field] = value

    for field, items in (patch.remove_items or {}).items():
        if field not in LIST_FIELDS:
            continue
        remove_set = {str(item) for item in items}
        data[field] = [item for item in data[field] if item not in remove_set]

    for field, items in (patch.replace_lists or {}).items():
        if field not in LIST_FIELDS:
            continue
        data[field] = list(dict.fromkeys(items or []))

    return ProjectSpecification.model_validate(data)


def _coerce_patch(value: Any) -> SpecificationPatch:
    if isinstance(value, SpecificationPatch):
        return value
    if isinstance(value, BaseModel):
        return SpecificationPatch.model_validate(value.model_dump(exclude_none=True))
    return SpecificationPatch.model_validate(_parse_json_content(value))


def extract_specification_update(
    current: ProjectSpecification,
    user_input: str,
    llm: Any,
    max_retries: int = 1,
) -> ProjectSpecification:
    """使用 LLM 抽取增量信息，并合并到当前规格对象。"""
    if not user_input.strip():
        return current

    fast_patch = _fast_extract_patch(user_input)
    if fast_patch is not None:
        return merge_specification(current, fast_patch)

    prompt = _EXTRACTION_PROMPT.format(
        current_spec=current.model_dump_json()
    )
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=user_input),
    ]

    with phase("specification_extraction"):
        structured_llm = getattr(llm, "with_structured_output", None)
        for attempt in range(max_retries + 1):
            try:
                if structured_llm is not None:
                    result = structured_llm(SpecificationPatch).invoke(messages)
                    patch = _coerce_patch(result)
                else:
                    response = llm.invoke(messages)
                    patch = _coerce_patch(response.content)
                return merge_specification(current, patch)
            except Exception:
                if attempt < max_retries:
                    time.sleep(min(2**attempt, 4))
                structured_llm = None

        # 抽取失败时不能因一次模型格式抖动中断整轮对话，回退为空 patch。
        return current
