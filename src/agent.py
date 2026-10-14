"""DeepSeek 智能体工厂。

这里只负责读取配置、创建模型，并把依赖注入给 LangGraph 图构建器。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI

from .config import (
    CHAT_TEMPERATURE,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    UTILITY_TEMPERATURE,
)
from .graph import build_agent_graph
from .memory import AgentState
from .tools import TOOLS, SpecificationStore, build_specification_toolkit

__all__ = ["AgentState", "create_LLM", "create_agent"]


def _enable_langsmith_tracing() -> None:
    tracing = os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2")
    if not tracing or tracing.strip().lower() not in {"1", "true", "yes", "on"}:
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"


def _create_base_llm(
    api_key: str | None = None,
    model_name: str | None = None,
    temperature: float = 0,
) -> ChatOpenAI:
    _enable_langsmith_tracing()

    resolved_api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not resolved_api_key:
        raise ValueError("缺少 DEEPSEEK_API_KEY，请在 .env 中配置或传入 api_key。")

    return ChatOpenAI(
        api_key=resolved_api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL,
        model=model_name or os.getenv("DEEPSEEK_MODEL") or DEFAULT_MODEL,
        temperature=temperature,
    )


def create_LLM(
    api_key: str | None = None,
    model_name: str | None = None,
    tools: list[Any] | None = None,
) -> tuple[Any, ChatOpenAI]:
    """创建绑定了工具的模型，以及不带工具绑定的基础模型。"""
    base_llm = _create_base_llm(api_key=api_key, model_name=model_name)
    resolved_tools = TOOLS if tools is None else tools
    model = base_llm.bind_tools(resolved_tools)

    return model, base_llm


def create_agent(
    api_key: str | None = None,
    model_name: str | None = None,
    spec_store: SpecificationStore | None = None,
    output_dir: str | Path | None = None,
) -> Any:
    """创建带规格定义工具的 DeepSeek 智能体。"""
    utility_llm = _create_base_llm(
        api_key=api_key,
        model_name=model_name,
        temperature=UTILITY_TEMPERATURE,
    )
    chat_llm = _create_base_llm(
        api_key=api_key,
        model_name=model_name,
        temperature=CHAT_TEMPERATURE,
    )
    store = spec_store or SpecificationStore(output_dir=output_dir)
    specification_tools = build_specification_toolkit(
        store=store,
        llm=utility_llm,
    )
    tools = [*TOOLS, *specification_tools]
    model = chat_llm.bind_tools(tools)

    return build_agent_graph(
        model=model,
        summary_model=utility_llm,
        tools=tools,
    )
