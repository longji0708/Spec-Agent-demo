"""从自然语言中增量抽取规格信息。"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .schemas import ProjectSpecification, SpecificationPatch


_EXTRACTION_PROMPT = """\
你是需求规格抽取助手。请只从用户本轮输入中抽取新增或修正的信息。

规则：
1. 没有新信息的字段返回 null。
2. 列表字段只返回本轮新增的条目，不要重复已有条目。
3. 不要编造用户没有提供的信息。
4. 只输出 JSON，不要输出解释、Markdown 代码块或其他文字。

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


def should_extract_specification(user_input: str) -> bool:
    """跳过简单确认语，避免为无新增信息的回复调用 LLM。"""
    normalized = re.sub(r"[\s，。！？!?.,]+", "", user_input).lower()
    return normalized not in _SHORT_ACKNOWLEDGEMENTS


def _to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text", block)))
            else:
                parts.append(str(block))
        return " ".join(parts)
    return str(content)


def _parse_json_content(content: Any) -> dict[str, Any]:
    text = _to_text(content).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


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

    list_fields = {
        "target_users",
        "functional_requirements",
        "non_functional_requirements",
        "constraints",
        "deliverables",
        "validation_specs",
        "tech_stack",
        "risks",
    }

    for field, value in patch_data.items():
        if field in list_fields:
            data[field] = _merge_unique(data[field], value or [])
        elif value is not None:
            data[field] = value

    return ProjectSpecification.model_validate(data)


def extract_specification_update(
    current: ProjectSpecification,
    user_input: str,
    llm: Any,
) -> ProjectSpecification:
    """使用 LLM 抽取增量信息，并合并到当前规格对象。"""
    if not user_input.strip():
        return current

    prompt = _EXTRACTION_PROMPT.format(
        current_spec=current.model_dump_json()
    )
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=user_input),
    ]
    response = llm.invoke(messages)
    patch_data = _parse_json_content(response.content)
    patch = SpecificationPatch.model_validate(patch_data)
    return merge_specification(current, patch)
