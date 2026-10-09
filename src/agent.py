from __future__ import annotations

import os
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .tools import TOOLS

_DEFAULT_MODEL = "deepseek-chat"
_DEFAULT_BASE_URL = "https://api.deepseek.com"


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

    model = ChatOpenAI(
        api_key=resolved_api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL") or _DEFAULT_BASE_URL,
        model=model_name or os.getenv("DEEPSEEK_MODEL") or _DEFAULT_MODEL,
        temperature=0,
    ).bind_tools(TOOLS)

    def call_model(state: MessagesState) -> dict[str, list[Any]]:
        return {"messages": [model.invoke(state["messages"])]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile()
