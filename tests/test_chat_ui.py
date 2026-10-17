import unittest

from langchain_core.messages import AIMessageChunk, HumanMessage

from spec_agent.chat_ui import (
    astream_agent_replies,
    stream_agent_replies,
)


class FakeAgent:
    def stream(self, input, config, stream_mode):
        yield AIMessageChunk(content="你"), {"langgraph_node": "agent"}
        yield AIMessageChunk(content="好"), {"langgraph_node": "agent"}
        yield AIMessageChunk(content="内部结果"), {"langgraph_node": "tools"}


class StreamAgentRepliesTest(unittest.TestCase):
    def test_only_returns_agent_text_chunks(self) -> None:
        chunks = list(
            stream_agent_replies(
                FakeAgent(),
                HumanMessage(content="你好"),
                {},
            )
        )

        self.assertEqual(chunks, ["你", "好"])


class AsyncStreamAgentRepliesTest(unittest.IsolatedAsyncioTestCase):
    async def test_streams_chat_tokens_and_tool_progress(self) -> None:
        class FakeAsyncAgent:
            async def astream_events(self, input, config, version):
                yield {
                    "event": "on_tool_start",
                    "name": "extract_specification",
                    "tags": [],
                }
                yield {
                    "event": "on_chat_model_stream",
                    "tags": ["utility_model"],
                    "data": {"chunk": AIMessageChunk(content="内部")},
                }
                yield {
                    "event": "on_chat_model_stream",
                    "tags": ["chat_model"],
                    "data": {"chunk": AIMessageChunk(content="你好")},
                }

        chunks = [
            text
            async for text in astream_agent_replies(
                FakeAsyncAgent(),
                HumanMessage(content="测试"),
                {},
            )
        ]

        self.assertIn("正在整理需求", "".join(chunks))
        self.assertIn("你好", "".join(chunks))
        self.assertNotIn("内部", "".join(chunks))

    async def test_tool_progress_text_is_marked_separately(self) -> None:
        class FakeAsyncAgent:
            async def astream_events(self, input, config, version):
                yield {
                    "event": "on_tool_start",
                    "name": "extract_specification",
                    "tags": [],
                }
                yield {
                    "event": "on_chat_model_stream",
                    "tags": ["chat_model"],
                    "data": {"chunk": AIMessageChunk(content="你好")},
                }

        chunks = [
            text
            async for text in astream_agent_replies(
                FakeAsyncAgent(),
                HumanMessage(content="测试"),
                {},
            )
        ]

        self.assertTrue(getattr(chunks[0], "is_progress", False))
        self.assertFalse(getattr(chunks[1], "is_progress", False))


if __name__ == "__main__":
    unittest.main()
