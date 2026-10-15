"""会话状态与摘要式短期记忆的门面模块。

具体实现已经拆分到：
- tokenizer.py
- history_window.py
- message_sanitizer.py
- summarizer.py
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages

from .history_window import split_messages
from .message_sanitizer import sanitize_messages
from .messages import content_to_text
from .summarizer import merge_summaries, summarize_history
from .tokenizer import count_tokens


class AgentState(TypedDict):
    """LangGraph 的会话状态。"""

    messages: Annotated[list[BaseMessage], add_messages]
    memory_summary: str
    summarized_count: int
    last_summarized_message_id: str | None


class MemoryContext(TypedDict):
    """一次模型调用所需的上下文数据。"""

    recent_messages: list[BaseMessage]
    memory_summary: str
    summarized_count: int
    last_summarized_message_id: str | None


def _message_identity(message: BaseMessage) -> str:
    """优先使用消息自带 ID；测试/旧消息没有 ID 时退化为内容指纹。"""
    message_id = getattr(message, "id", None)
    if message_id:
        return str(message_id)
    text = content_to_text(getattr(message, "content", ""))
    message_type = type(message).__name__
    return f"{message_type}:{text}"


def _message_index_after_last(
    identities: list[str],
    last_summarized_message_id: str | None,
) -> int | None:
    """返回完整消息列表中，最后一个已摘要消息的下一个索引。"""
    if not last_summarized_message_id:
        return None
    for index in range(len(identities) - 1, -1, -1):
        if identities[index] == last_summarized_message_id:
            return index + 1
    return None


def _summarized_overflow_count(
    overflow_count: int,
    full_message_count: int,
    full_index_after_last: int | None,
    fallback_count: int,
) -> int:
    """根据稳定的消息位置计算 overflow 中已经摘要过的条数。"""
    if full_index_after_last is not None:
        overflow_start = full_message_count - overflow_count
        return max(0, min(full_index_after_last - overflow_start, overflow_count))
    return min(fallback_count, overflow_count)


def build_memory_context(
    messages: list[BaseMessage],
    current_summary: str,
    summarized_count: int,
    max_tokens: int,
    summary_llm: ChatOpenAI,
    last_summarized_message_id: str | None = None,
    max_single_message_tokens: int | None = None,
    max_summary_tokens: int | None = None,
    summarize: bool = True,
    min_summary_messages: int = 1,
    summary_token_budget: int = 0,
) -> MemoryContext:
    """生成最近消息，并在允许时增量更新旧消息摘要。"""
    recent_messages, overflow_messages = split_messages(
        messages,
        max_tokens,
        max_single_message_tokens=max_single_message_tokens,
    )
    if not overflow_messages or not summarize:
        return {
            "recent_messages": recent_messages,
            "memory_summary": current_summary,
            "summarized_count": summarized_count,
            "last_summarized_message_id": last_summarized_message_id,
        }

    full_identities = [_message_identity(message) for message in messages]
    full_index_after_last = _message_index_after_last(
        full_identities,
        last_summarized_message_id,
    )
    safe_summarized_count = _summarized_overflow_count(
        len(overflow_messages),
        len(messages),
        full_index_after_last,
        summarized_count,
    )
    new_to_summarize = sanitize_messages(
        overflow_messages[safe_summarized_count:]
    )

    should_summarize = len(new_to_summarize) >= min_summary_messages or (
        sum(count_tokens(message) for message in new_to_summarize)
        >= summary_token_budget
    )

    if new_to_summarize and should_summarize:
        new_summary = summarize_history(new_to_summarize, summary_llm)
        current_summary = merge_summaries(
            current_summary,
            new_summary,
            llm=summary_llm,
            max_tokens=max_summary_tokens,
        )
        safe_summarized_count += len(new_to_summarize)
        last_summarized_message_id = _message_identity(new_to_summarize[-1])

    return {
        "recent_messages": recent_messages,
        "memory_summary": current_summary,
        "summarized_count": safe_summarized_count,
        "last_summarized_message_id": last_summarized_message_id,
    }
