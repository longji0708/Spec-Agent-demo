"""命令行对话的展示与流式输出。"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import AsyncIterator, Iterable
from typing import Any

from langchain_core.messages import AIMessageChunk

from .messages import content_to_text
from .timing import log_phase, timing_enabled

_CYAN = "\033[36m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_DIM = "\033[90m"
_RESET = "\033[0m"
_BOLD = "\033[1m"


class AgentProgressText(str):
    """进度提示文本，便于 CLI 与最终回复文本区分。"""

    is_progress = True


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


def _tool_progress_label(tool_name: str) -> str:
    labels = {
        "extract_specification": "正在整理需求",
        "check_missing_fields": "正在检查缺失项",
        "detect_specification_conflicts": "正在检查规格冲突",
        "render_specification_document": "正在生成规格文档",
    }
    return labels.get(tool_name, f"正在执行 {tool_name}")


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

        text = content_to_text(chunk.content)
        if text:
            yield text


async def astream_agent_replies(
    agent: Any,
    user_message: Any,
    config: dict[str, Any],
) -> AsyncIterator[str]:
    """流式输出 token，并在工具执行前给出轻量进度提示。"""
    first_token_started = time.perf_counter()
    first_token_seen = False
    tool_started_at: dict[str, float] = {}
    tool_call_count = 0
    total_started_at = first_token_started

    async for event in agent.astream_events(
        {"messages": [user_message]},
        config=config,
        version="v2",
    ):
        event_type = event.get("event")
        if event_type == "on_tool_start":
            tool_name = event.get("name") or "工具"
            tool_call_count += 1
            tool_started_at[event.get("run_id") or tool_name] = time.perf_counter()
            yield AgentProgressText(f"\n{hint(_tool_progress_label(tool_name))}\n")
            continue

        if event_type == "on_tool_end":
            tool_name = event.get("name") or "工具"
            started = tool_started_at.pop(event.get("run_id") or tool_name, None)
            if started is not None:
                log_phase(f"tool:{tool_name}", started)
            continue

        if event_type != "on_chat_model_stream":
            continue

        tags = set(event.get("tags") or [])
        if "chat_model" not in tags:
            continue

        chunk = event.get("data", {}).get("chunk")
        if not isinstance(chunk, AIMessageChunk):
            continue

        text = content_to_text(chunk.content)
        if not text:
            continue
        if not first_token_seen:
            first_token_seen = True
            log_phase("first_token", first_token_started)
        yield text

    log_phase("final_reply_total", total_started_at)
    if timing_enabled():
        log_phase(f"tool_call_count:{tool_call_count}", total_started_at)
