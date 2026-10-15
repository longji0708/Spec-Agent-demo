"""需求完整性校验。"""

from __future__ import annotations

from pydantic import BaseModel

from .schemas import ProjectSpecification


class MissingField(BaseModel):
    field: str
    label: str
    reason: str
    follow_up: str
    required: bool = True


class FieldRequirement(BaseModel):
    field: str
    label: str
    follow_up: str
    required: bool = True


REQUIRED_FIELDS: tuple[FieldRequirement, ...] = (
    FieldRequirement(
        field="project_name",
        label="项目名称",
        follow_up="请向用户询问：这个项目或产品叫什么名字？",
    ),
    FieldRequirement(
        field="target_users",
        label="目标用户",
        follow_up="请向用户询问：这个产品主要给谁使用，典型用户画像是什么？",
    ),
    FieldRequirement(
        field="functional_requirements",
        label="功能需求",
        follow_up="请向用户询问：用户最需要完成哪些核心功能？",
    ),
    FieldRequirement(
        field="non_functional_requirements",
        label="非功能需求",
        follow_up="请向用户询问：对性能、并发、响应时间、可用性、安全性有什么要求？",
    ),
    FieldRequirement(
        field="constraints",
        label="约束条件",
        follow_up="请向用户询问：成本、时间、平台、合规或技术限制是什么？",
    ),
    FieldRequirement(
        field="validation_specs",
        label="验证规格",
        follow_up="请向用户询问：怎样才算验收通过，有哪些可验证的验收标准？",
    ),
)

RECOMMENDED_FIELDS: tuple[FieldRequirement, ...] = (
    FieldRequirement(
        field="deliverables",
        label="交付物",
        follow_up="请向用户询问：最终需要交付哪些东西，例如原型、代码、文档？",
        required=False,
    ),
    FieldRequirement(
        field="tech_stack",
        label="技术栈",
        follow_up="请向用户询问：是否已有指定技术栈，或者希望采用哪些技术？",
        required=False,
    ),
    FieldRequirement(
        field="risks",
        label="风险",
        follow_up="请向用户询问：目前已知哪些项目风险？",
        required=False,
    ),
)

_PERFORMANCE_KEYWORDS = (
    "性能",
    "并发",
    "响应时间",
    "延迟",
    "吞吐",
    "qps",
    "tps",
    "可用性",
    "sla",
)


def _has_performance_indicator(specification: ProjectSpecification) -> bool:
    text = " ".join(specification.non_functional_requirements).lower()
    return any(keyword in text for keyword in _PERFORMANCE_KEYWORDS)


def check_missing_fields(
    specification: ProjectSpecification,
    required_only: bool = False,
) -> list[MissingField]:
    """返回缺失字段，并给出可读的追问话术。"""
    missing: list[MissingField] = []
    requirements = (
        REQUIRED_FIELDS if required_only else REQUIRED_FIELDS + RECOMMENDED_FIELDS
    )

    for requirement in requirements:
        value = getattr(specification, requirement.field)
        if not value:
            missing.append(
                MissingField(
                    field=requirement.field,
                    label=requirement.label,
                    reason=f"{requirement.label}尚未填写",
                    follow_up=requirement.follow_up,
                    required=requirement.required,
                )
            )

    if (
        not required_only
        and specification.non_functional_requirements
        and not _has_performance_indicator(specification)
    ):
        missing.append(
            MissingField(
                field="non_functional_requirements.performance",
                label="性能指标",
                reason="已有非功能需求，但缺少并发用户数、响应时间等性能指标",
                follow_up="缺少并发用户数、响应时间指标，请向用户询问",
                required=False,
            )
        )

    return missing
