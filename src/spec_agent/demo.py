"""无需真实 API Key 的本地演示模型。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.runnables import RunnableConfig


class DemoChatModel:
    """按固定脚本运行的轻量模型，用于演示和端到端测试。

    第一次调用时发出一个 ``extract_specification`` 工具调用；工具返回后，
    后续调用直接输出最终回复。该实现不依赖网络或真实 API Key。
    """

    def __init__(
        self,
        *,
        final_text: str = "我已经记录下这个示例项目，可以继续补充目标用户和功能需求。",
        tool_call_id: str = "call_demo_specification",
    ) -> None:
        self._final_text = final_text
        self._tool_call_id = tool_call_id
        self._has_called_tool = False

    def bind_tools(self, tools: list[Any]) -> DemoChatModel:
        self._tools = tools
        return self

    def invoke(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        """返回最终文本，供后台摘要等同步调用路径使用。"""
        del messages, config, kwargs
        return AIMessage(content=self._final_text)

    def stream(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Iterator[AIMessageChunk]:
        del messages, config, kwargs
        if not self._has_called_tool:
            self._has_called_tool = True
            yield AIMessageChunk(
                content="",
                id=self._tool_call_id,
                tool_calls=[
                    {
                        "name": "extract_specification",
                        "args": {
                            "user_input": "项目叫演示项目",
                            "project_name": "演示项目",
                        },
                        "id": self._tool_call_id,
                        "type": "tool_call",
                    }
                ],
            )
            return

        for character in self._final_text:
            yield AIMessageChunk(content=character)


def create_demo_models() -> tuple[DemoChatModel, DemoChatModel]:
    """创建可供 ``create_agent`` 注入的对话模型和工具模型。"""
    return DemoChatModel(), DemoChatModel(final_text="")
