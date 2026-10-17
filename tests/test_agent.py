import unittest

from spec_agent.agent import create_agent


class CreateAgentTest(unittest.TestCase):
    def test_create_graph_with_fake_key(self) -> None:
        agent = create_agent(api_key="sk-test")
        self.assertIsNotNone(agent)
        self.assertIn("agent", agent.get_graph().nodes)
        self.assertIn("tools", agent.get_graph().nodes)


if __name__ == "__main__":
    unittest.main()
