import unittest

from langchain_core.messages import AIMessageChunk, HumanMessage

from src.chat_ui import stream_agent_replies


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


if __name__ == "__main__":
    unittest.main()
