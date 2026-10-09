# tools.py
from typing import Any


def add(a: int, b: int) -> int:
    """计算两个整数的和。"""
    return a + b


TOOL_EXECUTORS = {
    "add": add,
}


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "计算两个整数的和。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "第一个整数"},
                    "b": {"type": "integer", "description": "第二个整数"},
                },
                "required": ["a", "b"],
            },
        },
    }
]