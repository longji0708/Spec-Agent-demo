"""基于 OpenAI 兼容接口的 LangGraph 智能体。

顶层导入保持轻量：只有真正使用运行时或领域对象时才加载 LangChain/LangGraph。
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "AgentState",
    "create_agent",
    "ProjectSpecification",
    "SpecificationPatch",
    "SpecificationStore",
    "build_specification_toolkit",
]

_TOOL_EXPORTS = {
    "ProjectSpecification",
    "SpecificationPatch",
    "SpecificationStore",
    "build_specification_toolkit",
}


def __getattr__(name: str) -> Any:
    if name == "AgentState":
        from .memory import AgentState

        return AgentState
    if name == "create_agent":
        from .agent import create_agent

        return create_agent
    if name in _TOOL_EXPORTS:
        from . import tools

        return getattr(tools, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
