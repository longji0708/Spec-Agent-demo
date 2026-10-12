"""DeepSeek 智能体工厂。

这里只负责读取配置、创建模型，并把依赖注入给 LangGraph 图构建器。
"""

from __future__ import annotations

import os
from typing import Any

from langchain_openai import ChatOpenAI

from .config import DEFAULT_BASE_URL, DEFAULT_MODEL
from .graph import build_agent_graph
from .memory import AgentState
from .tools import TOOLS

__all__ = ["AgentState", "create_deepseek_agent"]


def _enable_langsmith_tracing() -> None:
    tracing = os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2")
    if not tracing or tracing.strip().lower() not in {"1", "true", "yes", "on"}:
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"


def create_deepseek_agent(
    api_key: str | None = None,
    model_name: str | None = None,
) -> Any:
    """创建并返回调用 DeepSeek 的 LangGraph 智能体。"""
    _enable_langsmith_tracing()

    resolved_api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not resolved_api_key:
        raise ValueError("缺少 DEEPSEEK_API_KEY，请在 .env 中配置或传入 api_key。")

    base_llm = ChatOpenAI(
        api_key=resolved_api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL,
        model=model_name or os.getenv("DEEPSEEK_MODEL") or DEFAULT_MODEL,
        temperature=0,
    )

    model = base_llm.bind_tools(TOOLS)
    summary_model = base_llm

    return build_agent_graph(model=model, summary_model=summary_model)
