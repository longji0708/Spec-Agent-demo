"""命令行对话的展示与流式输出。"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from typing import Any

from langchain_core.messages import AIMessageChunk


_CYAN = "\033[36m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_DIM = "\033[90m"
_RESET = "\033[0m"
_BOLD = "\033[1m"


def _supports_color() -> bool:
    return sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def colorize(text: str, color: str) -> str:
    """在支持颜色的终端中给文本加 ANSI 颜色。"""
    if not _supports_color():
        return text
    return f"{color}{text}{_RESET}"


def user_label() -> str:
    return colorize("你", _CYAN)


def ai_label() -> str:
    return colorize("AI", _GREEN)


def error_label() -> str:
    return colorize("运行出错", _RED)


def hint(text: str) -> str:
    return colorize(text, f"{_BOLD}{_DIM}")


def _content_to_text(content: Any) -> str:
    """把 LangChain 消息 chunk 的 content 转成可打印文本。"""
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
                parts.append(str(block.get("text", block)))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def stream_agent_replies(
    agent: Any,
    user_message: Any,
    config: dict[str, Any],
) -> Iterable[str]:
    """流式输出 Agent 节点产生的文本，忽略工具节点的内部结果。"""
    for chunk, metadata in agent.stream(
        {"messages": [user_message]},
        config=config,
        stream_mode="messages",
    ):
        if metadata.get("langgraph_node") != "agent":
            continue
        if not isinstance(chunk, AIMessageChunk):
            continue

        text = _content_to_text(chunk.content)
        if text:
            yield text
