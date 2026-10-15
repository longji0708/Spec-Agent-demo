"""历史消息摘要。"""

from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .messages import content_to_text
from .timing import phase
from .tokenizer import count_text_tokens, truncate_text_tail

_SUMMARY_PROMPT = (
    "下面是历史对话，压缩成精简事实摘要，保留关键业务信息，不要冗余描述："
)


def summarize_history(messages: list[BaseMessage], llm: ChatOpenAI) -> str:
    """把一组旧消息压缩成一段简短摘要。"""
    if not messages:
        return ""

    with phase("history_summarization"):
        prompt_messages = [SystemMessage(content=_SUMMARY_PROMPT), *messages]
        response = llm.invoke(prompt_messages)
        return content_to_text(response.content).strip()


def merge_summaries(
    existing: str,
    new_summary: str,
    llm: ChatOpenAI | None = None,
    max_tokens: int | None = None,
) -> str:
    """合并新旧摘要，并在超过预算时触发二次压缩。"""
    if not existing:
        return new_summary
    if not new_summary:
        return existing

    combined = f"{existing}\n{new_summary}"
    if max_tokens is None or count_text_tokens(combined) <= max_tokens:
        return combined

    if llm is not None:
        try:
            compressed = _compress_summaries(existing, new_summary, llm)
            if compressed and count_text_tokens(compressed) <= max_tokens:
                return compressed
        except Exception:
            # 二次压缩失败时降级为硬截断，保证摘要不会无限增长。
            pass

    return truncate_text_tail(combined, max_tokens)


def _compress_summaries(
    existing: str,
    new_summary: str,
    llm: ChatOpenAI,
) -> str:
    prompt = (
        "请把下面两段历史摘要合并压缩成一段新的精简摘要，"
        "保留关键事实、需求决策和未解决的问题，不要逐条复述对话："
    )
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"旧摘要：\n{existing}\n\n新增摘要：\n{new_summary}"),
    ]
    response = llm.invoke(messages)
    return content_to_text(response.content).strip()
