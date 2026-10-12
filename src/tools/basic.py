"""基础工具定义。"""

from langchain_core.tools import tool


def add(a: int, b: int) -> int:
    """计算两个整数的和。"""
    return a + b


TOOLS = [tool(add)]
