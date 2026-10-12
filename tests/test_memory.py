import unittest
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage

from src.memory import build_memory_context, split_messages


class SplitMessagesTest(unittest.TestCase):
    def test_keeps_original_order(self) -> None:
        messages = [HumanMessage(content=f"m{index}") for index in range(6)]

        recent, overflow = split_messages(messages, max_tokens=10)

        self.assertEqual([message.content for message in recent], ["m1", "m2", "m3", "m4", "m5"])
        self.assertEqual([message.content for message in overflow], ["m0"])


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
