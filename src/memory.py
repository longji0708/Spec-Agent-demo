"""会话上下文与摘要式短期记忆。

这里的记忆只存在于当前进程的 LangGraph MemorySaver 中：
- 最近一段消息会完整保留在提示词里；
- 超出窗口的旧消息会被压缩成摘要；
- 每个进程退出后，完整消息和摘要都会随进程一起释放。
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

import tiktoken
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph 的会话状态。"""

    messages: Annotated[list[BaseMessage], add_messages]
    memory_summary: str
    summarized_count: int


class MemoryContext(TypedDict):
    """一次模型调用所需的上下文数据。"""

    recent_messages: list[BaseMessage]
    memory_summary: str
    summarized_count: int


_ENCODER = tiktoken.get_encoding("cl100k_base")

_SUMMARY_PROMPT = (
    "下面是历史对话，压缩成精简事实摘要，保留关键业务信息，不要冗余描述："
)


def _content_to_text(content: Any) -> str:
    """把 LangChain 消息的多种 content 形式安全地转成纯文本。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                parts.append(str(text) if text is not None else str(block))
            else:
                parts.append(str(block))
        return " ".join(parts)
    return str(content)


def count_tokens(message: BaseMessage) -> int:
    """估算单条消息占用的 token 数量。"""
    return len(_ENCODER.encode(_content_to_text(message.content)))


def split_messages(
    messages: list[BaseMessage], max_tokens: int
) -> tuple[list[BaseMessage], list[BaseMessage]]:
    """按时间从新到旧保留最近消息，返回 (最近消息, 待摘要消息)。

    返回值都保持原始的时间顺序。
    """
    recent_reversed: list[BaseMessage] = []
    overflow_reversed: list[BaseMessage] = []
    total_tokens = 0

    for message in reversed(messages):
        message_tokens = count_tokens(message)
        if total_tokens + message_tokens <= max_tokens:
            recent_reversed.append(message)
            total_tokens += message_tokens
        else:
            overflow_reversed.append(message)

    return list(reversed(recent_reversed)), list(reversed(overflow_reversed))


def summarize_history(messages: list[BaseMessage], llm: ChatOpenAI) -> str:
    """把一组旧消息压缩成一段简短摘要。"""
    if not messages:
        return ""

    prompt_messages = [SystemMessage(content=_SUMMARY_PROMPT), *messages]
    response = llm.invoke(prompt_messages)
    return _content_to_text(response.content).strip()


def _merge_summary(existing: str, new_summary: str) -> str:
    if not existing:
        return new_summary
    if not new_summary:
        return existing
    return f"{existing}\n{new_summary}"


def build_memory_context(
    messages: list[BaseMessage],
    current_summary: str,
    summarized_count: int,
    max_tokens: int,
    summary_llm: ChatOpenAI,
) -> MemoryContext:
    """生成最近消息，并增量更新旧消息摘要。

    `summarized_count` 用于标记已经压缩过的最旧消息数量，避免同一个前缀
    在每一轮都被重复送入摘要模型。
    """
    recent_messages, overflow_messages = split_messages(messages, max_tokens)
    if not overflow_messages:
        return {
            "recent_messages": recent_messages,
            "memory_summary": current_summary,
            "summarized_count": summarized_count,
        }

    # 正常情况下 overflow_messages 只会增长；这里做一次边界保护，
    # 即使上下文窗口或消息数量发生变化也不会出现负索引。
    safe_summarized_count = min(summarized_count, len(overflow_messages))
    new_to_summarize = overflow_messages[safe_summarized_count:]

    if new_to_summarize:
        new_summary = summarize_history(new_to_summarize, summary_llm)
        current_summary = _merge_summary(current_summary, new_summary)
        safe_summarized_count += len(new_to_summarize)

    return {
        "recent_messages": recent_messages,
        "memory_summary": current_summary,
        "summarized_count": safe_summarized_count,
    }
