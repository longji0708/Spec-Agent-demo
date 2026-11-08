"""把规格定义器的纯逻辑服务包装为 LangChain 工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from .conflicts import detect_conflicts
from .extraction import (
    extract_specification_update,
    merge_specification,
    should_extract_specification,
)
from .rendering import render_specification
from .schemas import SpecificationPatch
from .store import SpecificationStore
from .validation import check_missing_fields as validate_missing_fields


def _error_result(message: str) -> str:
    return json.dumps(
        {"status": "error", "message": message},
        ensure_ascii=False,
    )


def build_specification_toolkit(
    *,
    store: SpecificationStore,
    llm: Any,
) -> list[Any]:
    """构建绑定到当前 store 和 LLM 的工具列表。"""

    @tool
    def extract_specification(
        user_input: str,
        project_name: str | None = None,
        target_users: list[str] | str | None = None,
        functional_requirements: list[str] | str | None = None,
        non_functional_requirements: list[str] | str | None = None,
        constraints: list[str] | str | None = None,
        deliverables: list[str] | str | None = None,
        validation_specs: list[str] | str | None = None,
        tech_stack: list[str] | str | None = None,
        risks: list[str] | str | None = None,
        remove_items: dict[str, list[str]] | None = None,
        replace_lists: dict[str, list[str]] | None = None,
    ) -> str:
        """从用户输入中抽取规格信息，并增量更新当前规格对象。

        优先由主模型直接把本轮新增字段写入工具参数；只有当主模型无法可靠给出
        结构化字段时才回退到内部 utility LLM 抽取。
        """
        current = store.get()
        if should_extract_specification(user_input):
            patch = SpecificationPatch(
                project_name=project_name,
                target_users=target_users,
                functional_requirements=functional_requirements,
                non_functional_requirements=non_functional_requirements,
                constraints=constraints,
                deliverables=deliverables,
                validation_specs=validation_specs,
                tech_stack=tech_stack,
                risks=risks,
                remove_items=remove_items,
                replace_lists=replace_lists,
            )
            if patch.model_dump(exclude_none=True):
                updated = merge_specification(current, patch)
            else:
                updated = extract_specification_update(
                    current=current,
                    user_input=user_input,
                    llm=llm,
                )
        else:
            return json.dumps(
                {
                    "status": "skipped",
                    "message": "未检测到新的规格信息，未写入快照。",
                },
                ensure_ascii=False,
            )

        try:
            store.replace(updated)
            markdown_path = render_specification(
                updated,
                store.output_dir,
                "markdown",
            )
        except (OSError, ValueError) as exc:
            return _error_result(f"规格更新或快照生成失败：{exc}")
        missing = validate_missing_fields(updated)
        conflicts = detect_conflicts(updated)
        return json.dumps(
            {
                "status": "updated",
                "snapshot": str(markdown_path),
                "missing": [item.model_dump() for item in missing],
                "conflicts": [item.model_dump() for item in conflicts],
                "message": (
                    "已更新规格对象；请直接根据 missing 和 conflicts 结果继续追问。"
                ),
            },
            ensure_ascii=False,
        )

    @tool
    def check_missing_fields() -> str:
        """检查当前规格对象缺失字段，并区分必填/推荐项，返回追问建议。"""
        specification = store.get()
        missing = validate_missing_fields(specification)
        required_missing = validate_missing_fields(
            specification,
            required_only=True,
        )
        return json.dumps(
            {
                "complete": not required_missing,
                "missing": [item.model_dump() for item in missing],
                "guidance": (
                    "所有必填字段已填写，可进行冲突检测；建议再补充推荐字段。"
                    if not required_missing
                    else "请优先追问最关键的 1-3 个必填缺失项，不要一次问太多。"
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
                "conflicts": [item.model_dump() for item in conflicts],
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
        force: bool = False,
    ) -> str:
        """根据当前完整规格生成最终项目规格定义文档。

        Args:
            output_format: 可选 markdown、html、word。
            output_dir: 输出目录，默认为项目根目录。
            force: 即使仍有必填字段缺失或冲突，也强制导出。
        """
        specification = store.get()
        missing_required = validate_missing_fields(
            specification,
            required_only=True,
        )
        conflicts = detect_conflicts(specification)

        if not force and (missing_required or conflicts):
            return json.dumps(
                {
                    "status": "blocked",
                    "missing": [item.model_dump() for item in missing_required],
                    "conflicts": [item.model_dump() for item in conflicts],
                    "message": (
                        "仍有必填字段缺失或规格冲突，暂不生成最终文档。"
                        "请继续向用户澄清；如需强制导出，可传入 force=true。"
                    ),
                },
                ensure_ascii=False,
            )

        target_dir = Path(output_dir) if output_dir else store.output_dir
        try:
            target_dir.resolve().relative_to(store.output_dir.resolve())
        except ValueError:
            return _error_result(
                "输出目录必须位于当前项目的 output 根目录内，不能写入任意路径。"
            )

        try:
            output_path = render_specification(
                specification,
                target_dir,
                output_format,
            )
        except (OSError, ValueError) as exc:
            return _error_result(str(exc))
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
