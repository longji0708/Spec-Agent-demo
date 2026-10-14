"""需求完整性校验。"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .schemas import ProjectSpecification


@dataclass(frozen=True)
class MissingField:
    field: str
    label: str
    reason: str
    follow_up: str


REQUIRED_FIELDS: dict[str, str] = {
    "project_name": "项目名称",
    "target_users": "目标用户",
    "functional_requirements": "功能需求",
    "non_functional_requirements": "非功能需求",
    "constraints": "约束条件",
    "deliverables": "交付物",
    "validation_specs": "验证规格",
    "tech_stack": "技术栈",
}

_FOLLOW_UP_MESSAGES: dict[str, str] = {
    "project_name": "请向用户询问：这个项目或产品叫什么名字？",
    "target_users": "请向用户询问：这个产品主要给谁使用，典型用户画像是什么？",
    "functional_requirements": "请向用户询问：用户最需要完成哪些核心功能？",
    "non_functional_requirements": (
        "请向用户询问：对性能、并发、响应时间、可用性、安全性有什么要求？"
    ),
    "constraints": "请向用户询问：成本、时间、平台、合规或技术限制是什么？",
    "deliverables": "请向用户询问：最终需要交付哪些东西，例如原型、代码、文档？",
    "validation_specs": "请向用户询问：怎样才算验收通过，有哪些可验证的验收标准？",
    "tech_stack": "请向用户询问：是否已有指定技术栈，或者希望采用哪些技术？",
}

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
) -> list[MissingField]:
    """返回缺失字段，并给出可读的追问话术。"""
    missing: list[MissingField] = []

    for field, label in REQUIRED_FIELDS.items():
        value = getattr(specification, field)
        if not value:
            missing.append(
                MissingField(
                    field=field,
                    label=label,
                    reason=f"{label}尚未填写",
                    follow_up=_FOLLOW_UP_MESSAGES[field],
                )
            )

    if (
        specification.non_functional_requirements
        and not _has_performance_indicator(specification)
    ):
        missing.append(
            MissingField(
                field="non_functional_requirements.performance",
                label="性能指标",
                reason="已有非功能需求，但缺少并发用户数、响应时间等性能指标",
                follow_up="缺少并发用户数、响应时间指标，请向用户询问",
            )
        )

    return missing


def missing_fields_to_dict(
    missing_fields: list[MissingField],
) -> list[dict[str, str]]:
    return [asdict(item) for item in missing_fields]
