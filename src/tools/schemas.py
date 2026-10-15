"""规格定义器的领域模型。"""

from __future__ import annotations

from typing import get_origin

from pydantic import BaseModel, Field


class ProjectSpecification(BaseModel):
    """项目规格定义器的完整结构化状态。"""

    project_name: str = Field(default="", description="项目名称")
    target_users: list[str] = Field(
        default_factory=list, description="目标用户或用户画像"
    )
    functional_requirements: list[str] = Field(
        default_factory=list, description="功能需求列表"
    )
    non_functional_requirements: list[str] = Field(
        default_factory=list,
        description="非功能需求，例如性能、可用性、安全性、可维护性",
    )
    constraints: list[str] = Field(
        default_factory=list, description="约束条件，例如成本、时间、平台、合规"
    )
    deliverables: list[str] = Field(
        default_factory=list, description="交付物列表"
    )
    validation_specs: list[str] = Field(
        default_factory=list, description="验证规格或验收标准"
    )
    tech_stack: list[str] = Field(
        default_factory=list, description="技术栈或技术选型"
    )
    risks: list[str] = Field(default_factory=list, description="风险列表")


class SpecificationPatch(BaseModel):
    """单轮对话中需要增量写入规格对象的字段。

    未获得新信息的字段应为 ``None``；列表字段只放入本轮新增内容，
    后续会与已有内容合并，从而避免旧信息被 LLM 省略时丢失。

    ``remove_items`` 用于删除列表字段中的已有条目；``replace_lists``
    用于用户明确要求“改成/不要再用”时，完整覆盖目标列表字段。
    """

    project_name: str | None = Field(default=None, description="项目名称")
    target_users: list[str] | None = Field(
        default=None, description="目标用户或用户画像"
    )
    functional_requirements: list[str] | None = Field(
        default=None, description="功能需求列表"
    )
    non_functional_requirements: list[str] | None = Field(
        default=None, description="非功能需求列表"
    )
    constraints: list[str] | None = Field(
        default=None, description="约束条件列表"
    )
    deliverables: list[str] | None = Field(
        default=None, description="交付物列表"
    )
    validation_specs: list[str] | None = Field(
        default=None, description="验证规格列表"
    )
    tech_stack: list[str] | None = Field(default=None, description="技术栈列表")
    risks: list[str] | None = Field(default=None, description="风险列表")
    remove_items: dict[str, list[str]] | None = Field(
        default=None,
        description=(
            "需要从已有列表字段删除的条目。键必须是规格中的列表字段名，"
            "例如 {'tech_stack': ['Vue']}。"
        ),
    )
    replace_lists: dict[str, list[str]] | None = Field(
        default=None,
        description=(
            "需要整体替换的列表字段。用户说“登录改成扫码登录”“技术栈改成 React”"
            "等覆盖性修改时使用，值必须是修改后希望保留的完整列表。"
        ),
    )


LIST_FIELDS: frozenset[str] = frozenset(
    field_name
    for field_name, field in ProjectSpecification.model_fields.items()
    if get_origin(field.annotation) is list
)
