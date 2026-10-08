import unittest

from src.agent import add, create_deepseek_agent


class AddToolTest(unittest.TestCase):
    def test_add(self) -> None:
        self.assertEqual(add(2, 3), 5)


class CreateAgentTest(unittest.TestCase):
    def test_create_graph_with_fake_key(self) -> None:
        agent = create_deepseek_agent(api_key="sk-test")
        self.assertIsNotNone(agent)


if __name__ == "__main__":
    unittest.main()
