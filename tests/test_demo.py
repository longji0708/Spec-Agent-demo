import tempfile
import unittest
from pathlib import Path

from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage

from spec_agent.demo import create_demo_models
from spec_agent.runtime import create_agent
from spec_agent.tools.store import SpecificationStore


class DemoEndToEndTest(unittest.TestCase):
    def test_demo_model_runs_agent_tool_agent_flow_without_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            chat_model, utility_model = create_demo_models()
            store = SpecificationStore(output_dir=tmp_dir)
            agent = create_agent(
                chat_model=chat_model,
                utility_model=utility_model,
                spec_store=store,
            )

            streamed = list(
                agent.stream(
                    {"messages": [HumanMessage(content="演示")]},
                    config={"configurable": {"thread_id": "demo-e2e"}},
                    stream_mode="messages",
                )
            )

            chunks = [chunk for chunk, _ in streamed]
            text = "".join(
                getattr(chunk, "content", "")
                for chunk in chunks
                if getattr(chunk, "content", "")
            )

            self.assertTrue(any(isinstance(chunk, ToolMessage) for chunk in chunks))
            self.assertEqual(store.get().project_name, "演示项目")
            self.assertIn("我已经记录下这个示例项目", text)
            self.assertTrue((Path(tmp_dir) / "specification.md").exists())

    def test_demo_model_supports_background_summary_invoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            chat_model, utility_model = create_demo_models()
            agent = create_agent(
                chat_model=chat_model,
                utility_model=utility_model,
                spec_store=SpecificationStore(output_dir=tmp_dir),
                max_history_tokens=1,
            )
            config = {"configurable": {"thread_id": "demo-summary"}}

            list(
                agent.stream(
                    {"messages": [HumanMessage(content="演示")]},
                    config=config,
                    stream_mode="messages",
                )
            )
            agent.finalize_memory(config)

            self.assertEqual(chat_model.invoke([]).content, chat_model._final_text)

    def test_streaming_tool_call_chunks_are_merged_before_state_update(self) -> None:
        class StreamingToolCallModel:
            def __init__(self) -> None:
                self.called_tool = False

            def bind_tools(self, tools):
                self.tools = tools
                return self

            def stream(self, messages, config=None, **kwargs):
                if not self.called_tool:
                    self.called_tool = True
                    yield AIMessageChunk(
                        content="",
                        id="call_stream",
                        tool_calls=[
                            {
                                "name": "extract_specification",
                                "args": {
                                    "user_input": "项目叫流式项目",
                                    "project_name": "流式项目",
                                },
                                "id": "call_stream",
                                "type": "tool_call",
                            }
                        ],
                    )
                    yield AIMessageChunk(content="", id="call_stream")
                else:
                    yield AIMessageChunk(content="流式工具调用已完成")

            def invoke(self, messages, config=None, **kwargs):
                return AIMessageChunk(content="流式工具调用已完成")

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SpecificationStore(output_dir=tmp_dir)
            _, utility_model = create_demo_models()
            agent = create_agent(
                chat_model=StreamingToolCallModel(),
                utility_model=utility_model,
                spec_store=store,
            )

            streamed = list(
                agent.stream(
                    {"messages": [HumanMessage(content="流式演示")]},
                    config={"configurable": {"thread_id": "streaming-tool-call"}},
                    stream_mode="messages",
                )
            )
            chunks = [chunk for chunk, _ in streamed]
            text = "".join(
                getattr(chunk, "content", "")
                for chunk in chunks
                if getattr(chunk, "content", "")
            )

            self.assertTrue(any(isinstance(chunk, ToolMessage) for chunk in chunks))
            self.assertEqual(store.get().project_name, "流式项目")
            self.assertIn("流式工具调用已完成", text)


if __name__ == "__main__":
    unittest.main()
