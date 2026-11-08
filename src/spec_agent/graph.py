"""LangGraph 图定义与节点逻辑。"""

from __future__ import annotations

from datetime import datetime
from functools import partial
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    message_chunk_to_message,
)
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from .config import (
    MAX_MEMORY_SUMMARY_TOKENS,
    MAX_SINGLE_MESSAGE_TOKENS,
)
from .memory import AgentState, MemoryContext, build_memory_context
from .message_sanitizer import sanitize_messages
from .messages import content_to_text
from .prompts import build_system_prompt
from .timing import phase


def _extract_already_executed(messages: list[Any], current_message: Any) -> bool:
    """判断当前轮是否已经执行过一次 ``extract_specification``。"""
    turn_start = 0
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            turn_start = index
            break

    for message in messages[turn_start:]:
        if message is current_message:
            continue
        if isinstance(message, ToolMessage) and message.name == "extract_specification":
            return True
        if isinstance(message, AIMessage):
            tool_calls = message.tool_calls or []
            if any(
                tool_call.get("name") == "extract_specification"
                for tool_call in tool_calls
            ):
                return True
    return False


def route_after_agent(state: AgentState) -> str:
    """替换默认 ``tools_condition``，限制 ``extract_specification`` 每轮只执行一次。"""
    messages = state.get("messages", [])
    if not messages:
        return END

    current_message = messages[-1]
    if not isinstance(current_message, AIMessage) or not current_message.tool_calls:
        return END
    current_tool_names = {
        tool_call.get("name") for tool_call in (current_message.tool_calls or [])
    }
    if "extract_specification" in current_tool_names and _extract_already_executed(
        messages,
        current_message,
    ):
        return "force_text"
    return "tools"


def _merge_streamed_message(response_chunks: list[Any]) -> list[Any]:
    if not response_chunks:
        return []
    merged_chunk = response_chunks[0]
    for chunk in response_chunks[1:]:
        merged_chunk = merged_chunk + chunk
    return [message_chunk_to_message(merged_chunk)]


def _build_model_input(
    state: AgentState,
    config: RunnableConfig,
    *,
    messages: list[Any] | None,
    summary_model: Any,
    default_user_role: str,
    default_scene_rule: str,
    max_history_tokens: int,
) -> tuple[list[BaseMessage], MemoryContext]:
    cfg = config.get("configurable", {}) if config else {}
    user_role = cfg.get("user_role") or default_user_role
    scene_rule = cfg.get("scene_rule") or default_scene_rule
    current_time = cfg.get("current_time")
    if not current_time:
        current_time = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    source_messages = state["messages"] if messages is None else messages
    with phase("build_memory_context"):
        context = build_memory_context(
            messages=source_messages,
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
    model_messages = [
        SystemMessage(content=system_prompt),
        *recent_messages,
    ]
    return model_messages, context


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
    model_messages, context = _build_model_input(
        state,
        config,
        messages=None,
        summary_model=summary_model,
        default_user_role=default_user_role,
        default_scene_rule=default_scene_rule,
        max_history_tokens=max_history_tokens,
    )
    with phase("chat_model_stream"):
        response_chunks = list(model.stream(model_messages, config=config))
    response_messages = _merge_streamed_message(response_chunks)
    return {
        "messages": response_messages,
        "memory_summary": context["memory_summary"],
        "summarized_count": context["summarized_count"],
        "last_summarized_message_id": context["last_summarized_message_id"],
    }


def force_text(
    state: AgentState,
    config: RunnableConfig,
    *,
    model: Any,
    summary_model: Any,
    default_user_role: str,
    default_scene_rule: str,
    max_history_tokens: int,
) -> dict[str, Any]:
    """把工具调用历史重写为纯文本后，强制生成最终回复。"""
    messages = list(state.get("messages", []))
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        messages = messages[:-1]

    cfg = config.get("configurable", {}) if config else {}
    user_role = cfg.get("user_role") or default_user_role
    scene_rule = cfg.get("scene_rule") or default_scene_rule
    current_time = cfg.get("current_time")
    if not current_time:
        current_time = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    system_prompt = build_system_prompt(
        memory_summary=state.get("memory_summary", ""),
        user_role=user_role,
        scene_rule=scene_rule,
        current_time=current_time,
    )
    text_messages: list[Any] = [SystemMessage(content=system_prompt)]
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            text = content_to_text(message.content)
            if not text.strip():
                continue
        if isinstance(message, ToolMessage):
            text_messages.append(
                HumanMessage(content=f"工具执行结果：{content_to_text(message.content)}")
            )
        elif isinstance(message, HumanMessage):
            text_messages.append(HumanMessage(content=content_to_text(message.content)))
        elif isinstance(message, AIMessage):
            text = content_to_text(message.content)
            if text.strip():
                text_messages.append(HumanMessage(content=text))
    text_messages.append(
        HumanMessage(
            content=(
                "请基于这些信息，用简短的中文自然语言回复用户，"
                "不要调用工具，也不要输出工具调用。"
            )
        )
    )

    with phase("force_text_stream"):
        response_chunks = list(model.stream(text_messages, config=config))
    response_messages = _merge_streamed_message(response_chunks)
    return {
        "messages": response_messages,
        "memory_summary": state.get("memory_summary", ""),
        "summarized_count": state.get("summarized_count", 0),
        "last_summarized_message_id": state.get("last_summarized_message_id"),
    }


def build_agent_graph(
    *,
    model: Any,
    force_text_model: Any,
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
    force_text_node = partial(
        force_text,
        model=force_text_model,
        summary_model=summary_model,
        default_user_role=default_user_role,
        default_scene_rule=default_scene_rule,
        max_history_tokens=max_history_tokens,
    )

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model_1)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("force_text", force_text_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent)
    graph.add_edge("tools", "agent")
    graph.add_edge("force_text", END)

    return graph.compile(checkpointer=MemorySaver())
