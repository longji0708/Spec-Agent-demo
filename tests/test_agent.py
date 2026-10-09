import unittest

from src.agent import create_deepseek_agent
from src.tools import add


class AddToolTest(unittest.TestCase):
    def test_add(self) -> None:
        self.assertEqual(add(2, 3), 5)


class CreateAgentTest(unittest.TestCase):
    def test_create_graph_with_fake_key(self) -> None:
        agent = create_deepseek_agent(api_key="sk-test")
        self.assertIsNotNone(agent)
        self.assertIn("agent", agent.get_graph().nodes)
        self.assertIn("tools", agent.get_graph().nodes)


if __name__ == "__main__":
    unittest.main()
