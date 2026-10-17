"""消息 token 估算。"""

from __future__ import annotations

import json

import tiktoken
from langchain_core.messages import AIMessage, BaseMessage

from .messages import content_to_text

_ENCODER = tiktoken.get_encoding("cl100k_base")

# 粗略补齐 OpenAI 兼容接口中角色标识、消息分隔和工具调用格式带来的开销。
# 默认不直接加到 count_tokens 上，避免影响历史窗口测试的稳定语义；
# 预算层会统一留安全余量。
MESSAGE_FORMAT_OVERHEAD_TOKENS = 4


def count_text_tokens(text: str) -> int:
    """估算纯文本的 token 数量。"""
    return len(_ENCODER.encode(text))


def count_tokens(message: BaseMessage) -> int:
    """估算单条消息占用的 token 数量。"""
    text = content_to_text(message.content)
    if isinstance(message, AIMessage) and message.tool_calls:
        text += json.dumps(message.tool_calls, ensure_ascii=False)
    return count_text_tokens(text)


def truncate_text(text: str, max_tokens: int) -> str:
    """按 token 预算截断文本，保留开头部分。"""
    if max_tokens <= 0:
        return ""
    tokens = _ENCODER.encode(text)
    if len(tokens) <= max_tokens:
        return text
    if max_tokens == 1:
        return "…"
    return _ENCODER.decode(tokens[: max_tokens - 1]) + "…"


def truncate_text_tail(text: str, max_tokens: int) -> str:
    """按 token 预算截断文本，优先保留结尾部分，适合摘要。"""
    if max_tokens <= 0:
        return ""
    tokens = _ENCODER.encode(text)
    if len(tokens) <= max_tokens:
        return text
    if max_tokens == 1:
        return "…"
    return "…" + _ENCODER.decode(tokens[-(max_tokens - 1):])
