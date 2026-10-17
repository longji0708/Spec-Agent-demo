import unittest
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from spec_agent.memory import build_memory_context, sanitize_messages, split_messages
from spec_agent.tokenizer import count_text_tokens


class SplitMessagesTest(unittest.TestCase):
    def test_keeps_original_order(self) -> None:
        messages = [HumanMessage(content=f"m{index}") for index in range(6)]

        recent, overflow = split_messages(messages, max_tokens=10)

        self.assertEqual([message.content for message in recent], ["m1", "m2", "m3", "m4", "m5"])
        self.assertEqual([message.content for message in overflow], ["m0"])

    def test_keeps_tool_message_with_calling_ai(self) -> None:
        ai_message = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "extract_specification",
                    "args": {"user_input": "测试"},
                    "id": "call_1",
                    "type": "tool_call",
                }
            ],
        )
        tool_message = ToolMessage(
            content='{"status": "updated"}',
            tool_call_id="call_1",
        )

        recent, _ = split_messages(
            [HumanMessage(content="测试"), ai_message, tool_message],
            max_tokens=1,
        )

        message_types = [type(message).__name__ for message in recent]
        self.assertIn("AIMessage", message_types)
        self.assertIn("ToolMessage", message_types)
        self.assertLess(
            message_types.index("AIMessage"),
            message_types.index("ToolMessage"),
        )

    def test_sanitize_removes_orphan_tool_message(self) -> None:
        tool_message = ToolMessage(
            content='{"status": "updated"}',
            tool_call_id="missing_call",
        )

        sanitized = sanitize_messages(
            [HumanMessage(content="测试"), tool_message]
        )

        self.assertEqual(len(sanitized), 1)
        self.assertIsInstance(sanitized[0], HumanMessage)

    def test_truncates_single_oversized_message(self) -> None:
        huge_message = HumanMessage(content="x" * 5000)

        recent, overflow = split_messages(
            [huge_message],
            max_tokens=100,
            max_single_message_tokens=50,
        )

        self.assertEqual(len(recent), 1)
        self.assertLessEqual(count_text_tokens(recent[0].content), 50)
        self.assertEqual(overflow, [])


class BuildMemoryContextTest(unittest.TestCase):
    def test_does_not_resummarize_the_same_overflow_prefix(self) -> None:
        summary_llm = Mock()
        summary_llm.invoke.return_value = AIMessage(content="摘要")
        messages = [HumanMessage(content=f"m{index}") for index in range(6)]

        first = build_memory_context(
            messages=messages,
            current_summary="",
            summarized_count=0,
            max_tokens=10,
            summary_llm=summary_llm,
        )
        second = build_memory_context(
            messages=messages,
            current_summary=first["memory_summary"],
            summarized_count=first["summarized_count"],
            max_tokens=10,
            summary_llm=summary_llm,
        )

        self.assertEqual(first["summarized_count"], 1)
        self.assertEqual(second["summarized_count"], 1)
        summary_llm.invoke.assert_called_once()


if __name__ == "__main__":
    unittest.main()
