"""LangChain 消息内容与纯文本转换工具。"""

from __future__ import annotations

from typing import Any


def content_to_text(content: Any) -> str:
    """把消息 content 的多种表示统一转换成纯文本。"""
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
