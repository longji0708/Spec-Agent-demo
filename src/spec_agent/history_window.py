"""最近消息窗口切分。"""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from .message_sanitizer import group_messages
from .messages import content_to_text
from .tokenizer import count_text_tokens, count_tokens, truncate_text


def _truncate_message(message: BaseMessage, max_tokens: int) -> BaseMessage:
    """截断单条消息的文本内容，同时尽量保留 tool_calls 结构。"""
    if count_tokens(message) <= max_tokens:
        return message

    text = content_to_text(message.content)
    if isinstance(message, AIMessage) and message.tool_calls:
        tool_tokens = count_text_tokens(
            json.dumps(message.tool_calls, ensure_ascii=False)
        )
        content_budget = max(0, max_tokens - tool_tokens)
        return message.model_copy(
            update={"content": truncate_text(text, content_budget)}
        )

    if isinstance(message, ToolMessage):
        return message.model_copy(
            update={"content": truncate_text(text, max_tokens)}
        )

    return message.model_copy(
        update={"content": truncate_text(text, max_tokens)}
    )


def _truncate_group(
    group: list[BaseMessage],
    max_group_tokens: int,
    max_single_message_tokens: int,
) -> list[BaseMessage]:
    """把一组消息压到预算内，同时保留 AI 与 ToolMessage 的对应关系。"""
    truncated: list[BaseMessage] = []
    remaining = max_group_tokens

    for index, message in enumerate(group):
        share = max(1, remaining // (len(group) - index))
        budget = min(share, max_single_message_tokens)
        new_message = _truncate_message(message, budget)
        truncated.append(new_message)
        remaining = max(0, remaining - count_tokens(new_message))

    return truncated


def split_messages(
    messages: list[BaseMessage],
    max_tokens: int,
    max_single_message_tokens: int | None = None,
) -> tuple[list[BaseMessage], list[BaseMessage]]:
    """按时间从新到旧保留最近消息，返回 (最近消息, 待摘要消息)。"""
    recent_groups_reversed: list[list[BaseMessage]] = []
    overflow_groups_reversed: list[list[BaseMessage]] = []
    total_tokens = 0
    single_message_limit = max_single_message_tokens or max_tokens

    for group in reversed(group_messages(messages)):
        group_tokens = sum(count_tokens(message) for message in group)
        if total_tokens == 0 or total_tokens + group_tokens <= max_tokens:
            kept_group = group
            if total_tokens == 0:
                kept_group = _truncate_group(
                    group,
                    max_tokens,
                    single_message_limit,
                )
            recent_groups_reversed.append(kept_group)
            total_tokens += sum(count_tokens(message) for message in kept_group)
        else:
            overflow_groups_reversed.append(
                _truncate_group(
                    group,
                    max_tokens,
                    single_message_limit,
                )
            )

    recent_messages = [
        message
        for group in reversed(recent_groups_reversed)
        for message in group
    ]
    overflow_messages = [
        message
        for group in reversed(overflow_groups_reversed)
        for message in group
    ]
    return recent_messages, overflow_messages
