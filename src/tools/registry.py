"""把规格定义器的纯逻辑服务包装为 LangChain 工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from .conflicts import conflicts_to_dict, detect_conflicts
from .extraction import extract_specification_update, should_extract_specification
from .rendering import render_specification
from .store import SpecificationStore
from .validation import check_missing_fields as validate_missing_fields
from .validation import missing_fields_to_dict


def build_specification_toolkit(
    *,
    store: SpecificationStore,
    llm: Any,
) -> list[Any]:
    """构建绑定到当前 store 和 LLM 的工具列表。"""

    @tool
    def extract_specification(user_input: str) -> str:
        """从用户输入中抽取规格信息，并增量更新当前规格对象。

        每轮对话收到新的需求信息后都应调用。
        """
        current = store.get()
        if should_extract_specification(user_input):
            updated = extract_specification_update(
                current=current,
                user_input=user_input,
                llm=llm,
            )
        else:
            updated = current

        store.replace(updated)
        markdown_path = render_specification(
            updated,
            store.output_dir,
            "markdown",
        )
        missing = validate_missing_fields(updated)
        conflicts = detect_conflicts(updated)
        return json.dumps(
            {
                "status": "updated",
                "specification": updated.model_dump(),
                "snapshot": str(markdown_path),
                "missing": missing_fields_to_dict(missing),
                "conflicts": conflicts_to_dict(conflicts),
                "message": (
                    "已更新规格对象；请直接根据 missing 和 conflicts 结果继续追问。"
                ),
            },
            ensure_ascii=False,
        )

    @tool
    def check_missing_fields() -> str:
        """检查当前规格对象还缺少哪些必填字段，并返回追问建议。"""
        missing = validate_missing_fields(store.get())
        return json.dumps(
            {
                "complete": not missing,
                "missing": missing_fields_to_dict(missing),
                "guidance": (
                    "所有必填字段已填写，可进行冲突检测。"
                    if not missing
                    else "请优先追问最关键的 1-3 个缺失项，不要一次问太多。"
                ),
            },
            ensure_ascii=False,
        )

    @tool
    def detect_specification_conflicts() -> str:
        """检查当前规格对象是否存在内部矛盾，并返回澄清建议。"""
        conflicts = detect_conflicts(store.get())
        return json.dumps(
            {
                "has_conflicts": bool(conflicts),
                "conflicts": conflicts_to_dict(conflicts),
                "guidance": (
                    "未发现明显冲突。"
                    if not conflicts
                    else "请使用自然语言向用户澄清这些冲突。"
                ),
            },
            ensure_ascii=False,
        )

    @tool
    def render_specification_document(
        output_format: str = "markdown",
        output_dir: str | None = None,
    ) -> str:
        """根据当前完整规格生成最终项目规格定义文档。

        Args:
            output_format: 可选 markdown、html、word。
            output_dir: 输出目录，默认为项目根目录。
        """
        target_dir = Path(output_dir) if output_dir else store.output_dir
        output_path = render_specification(
            store.get(),
            target_dir,
            output_format,
        )
        return json.dumps(
            {
                "status": "rendered",
                "format": output_format,
                "path": str(output_path),
            },
            ensure_ascii=False,
        )

    return [
        extract_specification,
        check_missing_fields,
        detect_specification_conflicts,
        render_specification_document,
    ]
