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
                chunk.content
                for chunk in chunks
                if isinstance(chunk, AIMessageChunk) and chunk.content
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


if __name__ == "__main__":
    unittest.main()
