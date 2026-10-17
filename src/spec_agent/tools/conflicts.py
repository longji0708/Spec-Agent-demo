"""规格内部冲突检测。"""

from __future__ import annotations

from pydantic import BaseModel

from .schemas import ProjectSpecification


class Conflict(BaseModel):
    code: str
    description: str
    suggestion: str
    evidence: list[str]


def _specification_text(specification: ProjectSpecification) -> str:
    return " ".join(
        specification.functional_requirements
        + specification.non_functional_requirements
        + specification.constraints
    )


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _matching_entries(
    specification: ProjectSpecification, patterns: tuple[str, ...]
) -> list[str]:
    return [
        item
        for item in (
            specification.constraints
            + specification.non_functional_requirements
            + specification.functional_requirements
        )
        if _matches_any(item.lower(), patterns)
    ]


_LOW_COST_PATTERNS = (
    "低成本",
    "预算有限",
    "预算低",
    "成本低",
    "便宜",
    "省钱",
)

_HIGH_CONCURRENCY_PATTERNS = (
    "高并发",
    "海量用户",
    "10万",
    "10 万",
    "100k",
    "十万",
    "百万",
    "千万",
    "亿级",
)

_OFFLINE_PATTERNS = ("离线", "无网络", "断网")

_REALTIME_SYNC_PATTERNS = (
    "实时同步",
    "实时协作",
    "云端同步",
    "强一致",
    "强实时",
)


def detect_conflicts(
    specification: ProjectSpecification,
) -> list[Conflict]:
    """检查规格中的常见矛盾。"""
    text = _specification_text(specification).lower()
    conflicts: list[Conflict] = []

    low_cost = _matches_any(text, _LOW_COST_PATTERNS)
    high_concurrency = _matches_any(text, _HIGH_CONCURRENCY_PATTERNS)
    if low_cost and high_concurrency:
        conflicts.append(
            Conflict(
                code="low_cost_vs_high_concurrency",
                description="规格中同时出现低成本/预算约束和高并发要求，两者可能存在矛盾。",
                suggestion="请向用户澄清：在预算有限的前提下，预期的并发规模是多少？是否有可接受的降级方案？",
                evidence=_matching_entries(
                    specification,
                    _LOW_COST_PATTERNS + _HIGH_CONCURRENCY_PATTERNS,
                ),
            )
        )

    offline = _matches_any(text, _OFFLINE_PATTERNS)
    realtime_sync = _matches_any(text, _REALTIME_SYNC_PATTERNS)
    if offline and realtime_sync:
        conflicts.append(
            Conflict(
                code="offline_vs_realtime_sync",
                description="规格中同时要求离线可用和强云端实时同步，网络断开时实时同步难以保证。",
                suggestion="请向用户澄清：离线场景下允许怎样的数据延迟？是否需要本地缓存或冲突解决策略？",
                evidence=_matching_entries(
                    specification,
                    _OFFLINE_PATTERNS + _REALTIME_SYNC_PATTERNS,
                ),
            )
        )

    return conflicts
