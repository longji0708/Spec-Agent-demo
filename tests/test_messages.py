import unittest

from spec_agent.messages import content_to_text


class ContentToTextTest(unittest.TestCase):
    def test_converts_none_and_string(self) -> None:
        self.assertEqual(content_to_text(None), "")
        self.assertEqual(content_to_text("你好"), "你好")

    def test_converts_content_blocks(self) -> None:
        self.assertEqual(
            content_to_text(["你好", {"text": "世界"}, 3]),
            "你好 世界 3",
        )


if __name__ == "__main__":
    unittest.main()
