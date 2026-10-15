"""工具包入口。

默认只导出纯 Pydantic 领域对象，避免单纯读取 schemas 时加载 LangChain。
"""

from __future__ import annotations

from typing import Any

from .schemas import ProjectSpecification, SpecificationPatch
from .store import SpecificationStore

__all__ = [
    "ProjectSpecification",
    "SpecificationPatch",
    "SpecificationStore",
    "build_specification_toolkit",
]


def __getattr__(name: str) -> Any:
    if name == "build_specification_toolkit":
        from .registry import build_specification_toolkit

        return build_specification_toolkit
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
