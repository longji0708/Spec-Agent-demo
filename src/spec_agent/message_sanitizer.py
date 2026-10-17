"""确保传给 OpenAI 兼容接口的消息序列合法。"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage


def group_messages(messages: list[BaseMessage]) -> list[list[BaseMessage]]:
    """把带 tool_calls 的 AIMessage 和其后的 ToolMessage 归为一组。"""
    groups: list[list[BaseMessage]] = []
    index = 0

    while index < len(messages):
        message = messages[index]
        if isinstance(message, AIMessage) and message.tool_calls:
            end = index + 1
            while end < len(messages) and isinstance(messages[end], ToolMessage):
                end += 1
            groups.append(messages[index:end])
            index = end
        else:
            groups.append([message])
            index += 1

    return groups


def _tool_call_id(tool_call: Any) -> str:
    if isinstance(tool_call, dict):
        return str(tool_call.get("id") or tool_call.get("tool_call_id") or "")
    return str(getattr(tool_call, "id", "") or "")


def sanitize_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """丢弃孤立 ToolMessage，并清理没有工具结果对应的 tool_calls。"""
    sanitized: list[BaseMessage] = []

    for group in group_messages(messages):
        first = group[0]
        if isinstance(first, ToolMessage):
            continue
        if not (isinstance(first, AIMessage) and first.tool_calls):
            sanitized.extend(group)
            continue

        tool_messages = [
            message
            for message in group[1:]
            if isinstance(message, ToolMessage)
        ]
        available_ids = {message.tool_call_id for message in tool_messages}
        valid_tool_calls = [
            tool_call
            for tool_call in first.tool_calls
            if _tool_call_id(tool_call) in available_ids
        ]

        ai_message = first.model_copy(update={"tool_calls": valid_tool_calls})
        sanitized.append(ai_message)

        if valid_tool_calls:
            valid_ids = {_tool_call_id(tool_call) for tool_call in valid_tool_calls}
            sanitized.extend(
                message
                for message in tool_messages
                if message.tool_call_id in valid_ids
            )

    return sanitized
