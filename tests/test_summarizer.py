import unittest
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage

from spec_agent.summarizer import merge_summaries, summarize_history
from spec_agent.tokenizer import count_text_tokens


class SummarizerTest(unittest.TestCase):
    def test_summarize_empty_messages_returns_empty_string(self) -> None:
        llm = Mock()

        self.assertEqual(summarize_history([], llm), "")
        llm.invoke.assert_not_called()

    def test_summarize_history_uses_llm_response(self) -> None:
        llm = Mock()
        llm.invoke.return_value = AIMessage(content="历史摘要")

        result = summarize_history([HumanMessage(content="用户需求")], llm)

        self.assertEqual(result, "历史摘要")
        llm.invoke.assert_called_once()

    def test_merge_summaries_under_budget_concatenates(self) -> None:
        existing = "旧摘要"
        new_summary = "新摘要"

        result = merge_summaries(existing, new_summary)

        self.assertEqual(result, "旧摘要\n新摘要")

    def test_merge_summaries_compresses_when_over_budget(self) -> None:
        existing = "旧摘要内容" * 30
        new_summary = "新摘要内容" * 30
        llm = Mock()
        llm.invoke.return_value = AIMessage(content="压缩后的摘要")

        result = merge_summaries(
            existing,
            new_summary,
            llm=llm,
            max_tokens=20,
        )

        self.assertEqual(result, "压缩后的摘要")
        llm.invoke.assert_called_once()

    def test_merge_summaries_truncates_when_compression_fails(self) -> None:
        existing = "旧摘要内容" * 30
        new_summary = "新摘要内容" * 30
        llm = Mock()
        llm.invoke.side_effect = RuntimeError("summary failed")

        result = merge_summaries(
            existing,
            new_summary,
            llm=llm,
            max_tokens=20,
        )

        self.assertLessEqual(count_text_tokens(result), 20)


if __name__ == "__main__":
    unittest.main()
