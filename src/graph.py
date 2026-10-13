"""LangGraph 图定义与节点逻辑。"""

from __future__ import annotations
from functools import partial

from typing import Any

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .config import (
    DEFAULT_SCENE_RULE,
    DEFAULT_USER_ROLE,
    MAX_HISTORY_TOKENS,
)
from .memory import AgentState, build_memory_context
from .prompts import build_system_prompt
from .tools import TOOLS

def call_model(
    state: AgentState,
    config: RunnableConfig,
    *,
    model: Any,
    summary_model: Any,
) -> dict[str, Any]:
    cfg = config.get("configurable", {}) if config else {}
    user_role = cfg.get("user_role", DEFAULT_USER_ROLE)
    scene_rule = cfg.get("scene_rule", DEFAULT_SCENE_RULE)
    current_time = cfg.get("current_time", "")
    context = build_memory_context(
        messages=state["messages"],
        current_summary=state.get("memory_summary", ""),
        summarized_count=state.get("summarized_count", 0),
        max_tokens=MAX_HISTORY_TOKENS,
        summary_llm=summary_model,
    )
    system_prompt = build_system_prompt(
        memory_summary=context["memory_summary"],
        user_role=user_role,
        scene_rule=scene_rule,
        current_time=current_time,
    )
    messages = [
        SystemMessage(content=system_prompt),
        *context["recent_messages"],
    ]
    response = model.invoke(messages)
    return {
        "messages": [response],
        "memory_summary": context["memory_summary"],
        "summarized_count": context["summarized_count"],
    }

def build_agent_graph(*, model: Any, summary_model: Any) -> Any:

    call_model_1 = partial(call_model, model=model, summary_model=summary_model)
    
    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model_1)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=MemorySaver())
