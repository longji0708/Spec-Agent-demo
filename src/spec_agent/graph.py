"""LangGraph 图定义与节点逻辑。"""

from __future__ import annotations

from datetime import datetime
from functools import partial
from typing import Any

from langchain_core.messages import SystemMessage, message_chunk_to_message
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .config import (
    MAX_MEMORY_SUMMARY_TOKENS,
    MAX_SINGLE_MESSAGE_TOKENS,
)
from .memory import AgentState, build_memory_context
from .message_sanitizer import sanitize_messages
from .prompts import build_system_prompt
from .timing import phase


def call_model(
    state: AgentState,
    config: RunnableConfig,
    *,
    model: Any,
    summary_model: Any,
    default_user_role: str,
    default_scene_rule: str,
    max_history_tokens: int,
) -> dict[str, Any]:
    cfg = config.get("configurable", {}) if config else {}
    user_role = cfg.get("user_role") or default_user_role
    scene_rule = cfg.get("scene_rule") or default_scene_rule
    current_time = cfg.get("current_time")
    if not current_time:
        current_time = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    with phase("build_memory_context"):
        context = build_memory_context(
            messages=state["messages"],
            current_summary=state.get("memory_summary", ""),
            summarized_count=state.get("summarized_count", 0),
            last_summarized_message_id=state.get("last_summarized_message_id"),
            max_tokens=max_history_tokens,
            max_single_message_tokens=MAX_SINGLE_MESSAGE_TOKENS,
            max_summary_tokens=MAX_MEMORY_SUMMARY_TOKENS,
            summary_llm=summary_model,
            summarize=False,
        )
    system_prompt = build_system_prompt(
        memory_summary=context["memory_summary"],
        user_role=user_role,
        scene_rule=scene_rule,
        current_time=current_time,
    )
    recent_messages = sanitize_messages(context["recent_messages"])
    messages = [
        SystemMessage(content=system_prompt),
        *recent_messages,
    ]
    with phase("chat_model_stream"):
        response_chunks = list(model.stream(messages, config=config))
    if response_chunks:
        merged_chunk = response_chunks[0]
        for chunk in response_chunks[1:]:
            merged_chunk = merged_chunk + chunk
        response_messages = [message_chunk_to_message(merged_chunk)]
    else:
        response_messages = []
    return {
        "messages": response_messages,
        "memory_summary": context["memory_summary"],
        "summarized_count": context["summarized_count"],
        "last_summarized_message_id": context["last_summarized_message_id"],
    }

def build_agent_graph(
    *,
    model: Any,
    summary_model: Any,
    tools: list[Any],
    default_user_role: str,
    default_scene_rule: str,
    max_history_tokens: int,
) -> Any:
    call_model_1 = partial(
        call_model,
        model=model,
        summary_model=summary_model,
        default_user_role=default_user_role,
        default_scene_rule=default_scene_rule,
        max_history_tokens=max_history_tokens,
    )

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model_1)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=MemorySaver())
