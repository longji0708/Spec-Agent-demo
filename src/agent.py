from __future__ import annotations

import json
import operator
import os
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from openai import OpenAI

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


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


class AgentState(TypedDict):
    messages: Annotated[list[dict[str, Any]], operator.add]


def _message_to_dict(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    return message


def _run_tool_calls(last_message: dict[str, Any]) -> list[dict[str, Any]]:
    tool_messages: list[dict[str, Any]] = []

    for tool_call in last_message.get("tool_calls") or []:
        function = tool_call.get("function") or {}
        name = function.get("name")

        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {}

        executor = TOOL_EXECUTORS.get(name)
        content = str(executor(**arguments)) if executor else f"未知工具: {name}"

        tool_messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "content": content,
            }
        )

    return tool_messages


def create_deepseek_agent(
    api_key: str | None = None,
    model_name: str | None = None,
) -> Any:
    """创建并返回调用 DeepSeek 的 LangGraph 智能体。"""
    if api_key is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise ValueError("缺少 DEEPSEEK_API_KEY，请在 .env 中配置或传入 api_key。")

    model_name = model_name or os.getenv("DEEPSEEK_MODEL") or DEFAULT_MODEL

    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    def call_model(state: AgentState) -> dict[str, list[dict[str, Any]]]:
        response = client.chat.completions.create(
            model=model_name,
            messages=state["messages"],
            tools=TOOLS,
            temperature=0,
        )
        message = response.choices[0].message
        return {"messages": [_message_to_dict(message)]}

    def call_tools(state: AgentState) -> dict[str, list[dict[str, Any]]]:
        return {"messages": _run_tool_calls(state["messages"][-1])}

    def route_after_agent(state: AgentState) -> str:
        if state["messages"][-1].get("tool_calls"):
            return "tools"
        return "end"

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", call_tools)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "agent")
    return graph.compile()
