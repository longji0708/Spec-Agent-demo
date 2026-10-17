import argparse
import asyncio
import io
import json
import os
import runpy
import tempfile
import time
import unittest
import warnings
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from pydantic import BaseModel

import spec_agent
import spec_agent.tools as tools_pkg
from spec_agent.chat_ui import (
    _supports_color,
    ai_label,
    astream_agent_replies,
    colorize,
    error_label,
    hint,
    stream_agent_replies,
    user_label,
)
from spec_agent.cli import (
    _log_summary_task_done,
    _run,
    _run_once,
)
from spec_agent.config import (
    Settings,
    _bool,
    _float,
    _int,
    _int_required,
)
from spec_agent.llm import create_base_llm, enable_langsmith_tracing
from spec_agent.memory import _message_index_after_last, _summarized_overflow_count
from spec_agent.message_sanitizer import _tool_call_id
from spec_agent.messages import content_to_text
from spec_agent.runtime import AgentRuntime
from spec_agent.summarizer import merge_summaries
from spec_agent.timing import log_phase, phase
from spec_agent.tokenizer import truncate_text, truncate_text_tail
from spec_agent.tools.extraction import (
    _coerce_patch,
    _fast_extract_patch,
    _parse_json_content,
    _split_list_items,
    extract_specification_update,
    merge_specification,
)
from spec_agent.tools.registry import build_specification_toolkit
from spec_agent.tools.rendering import render_docx
from spec_agent.tools.schemas import ProjectSpecification, SpecificationPatch
from spec_agent.tools.store import SpecificationStore


class JsonPatchLLM:
    def __init__(self, patch: SpecificationPatch) -> None:
        self._patch = patch

    def invoke(self, messages):
        return AIMessage(content=self._patch.model_dump_json(exclude_none=True))


class RaisingLLM:
    def invoke(self, messages):
        raise AssertionError("this LLM should not be called")


class StructuredPatchLLM:
    def __init__(self, patch: SpecificationPatch) -> None:
        self._patch = patch

    def with_structured_output(self, schema):
        runner = self
        return runner

    def invoke(self, messages):
        return self._patch


class StructuredBaseModelLLM:
    def __init__(self, value: BaseModel) -> None:
        self._value = value

    def with_structured_output(self, schema):
        runner = self
        return runner

    def invoke(self, messages):
        return self._value


class AlwaysFailingStructuredLLM:
    def with_structured_output(self, schema):
        runner = self
        return runner

    def invoke(self, messages):
        raise RuntimeError("structured extraction failed")


class LazyExportsTest(unittest.TestCase):
    def test_lazy_exports_are_resolved(self) -> None:
        self.assertTrue(callable(spec_agent.AgentState))
        self.assertTrue(callable(spec_agent.create_agent))
        self.assertTrue(issubclass(spec_agent.ProjectSpecification, BaseModel))
        self.assertTrue(issubclass(spec_agent.SpecificationPatch, BaseModel))
        self.assertTrue(issubclass(spec_agent.SpecificationStore, object))
        self.assertTrue(callable(spec_agent.build_specification_toolkit))

    def test_unknown_top_level_attribute_raises(self) -> None:
        with self.assertRaises(AttributeError):
            _ = spec_agent.definitely_missing

    def test_unknown_tool_attribute_raises(self) -> None:
        with self.assertRaises(AttributeError):
            _ = tools_pkg.definitely_missing


class EntryPointCoverageTest(unittest.TestCase):
    def test_package_main_guard_calls_cli(self) -> None:
        with patch("spec_agent.cli.main") as main:
            runpy.run_module("spec_agent", run_name="__main__")
            main.assert_called_once_with()

    def test_cli_main_guard_calls_main(self) -> None:
        args = argparse.Namespace(
            prompt="demo",
            demo=True,
            storage=None,
            project="demo",
        )
        with patch.object(
            argparse.ArgumentParser,
            "parse_args",
            return_value=args,
        ), patch(
            "asyncio.run",
            side_effect=lambda coro: coro.close(),
        ), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            runpy.run_module("spec_agent.cli", run_name="__main__")


class ChatUiCoverageTest(unittest.TestCase):
    def test_color_labels_when_terminal_supports_color(self) -> None:
        with patch.object(
            spec_agent.chat_ui.sys.stdout,
            "isatty",
            return_value=True,
        ), patch.dict(os.environ, {}, clear=True):
            self.assertTrue(_supports_color())
            self.assertIn("\033", colorize("文本", "\033[36m"))
            self.assertIn("\033", user_label())
            self.assertIn("\033", ai_label())
            self.assertIn("\033", error_label())
            self.assertIn("\033", hint("提示"))

    def test_stream_replies_skips_non_ai_chunks(self) -> None:
        class MixedAgent:
            def stream(self, input, config, stream_mode):
                yield "not-an-ai-chunk", {"langgraph_node": "agent"}
                yield AIMessageChunk(content=""), {"langgraph_node": "agent"}

        self.assertEqual(list(stream_agent_replies(MixedAgent(), HumanMessage("x"), {})), [])


class AsyncStreamAgentRepliesCoverageTest(unittest.IsolatedAsyncioTestCase):
    async def test_tool_end_and_non_stream_events_are_handled(self) -> None:
        class FakeAsyncAgent:
            async def astream_events(self, input, config, version):
                yield {
                    "event": "on_tool_start",
                    "name": "extract_specification",
                    "run_id": "run_1",
                }
                yield {
                    "event": "on_tool_end",
                    "name": "extract_specification",
                    "run_id": "run_1",
                }
                yield {"event": "on_chain_start", "name": "ignored"}
                yield {
                    "event": "on_chat_model_stream",
                    "tags": ["chat_model"],
                    "data": {"chunk": "not-a-chunk"},
                }
                yield {
                    "event": "on_chat_model_stream",
                    "tags": ["chat_model"],
                    "data": {"chunk": AIMessageChunk(content="")},
                }
                yield {
                    "event": "on_chat_model_stream",
                    "tags": ["chat_model"],
                    "data": {"chunk": AIMessageChunk(content="你好")},
                }

        with patch("spec_agent.chat_ui.timing_enabled", return_value=True):
            chunks = [
                text
                async for text in astream_agent_replies(
                    FakeAsyncAgent(),
                    HumanMessage(content="测试"),
                    {},
                )
            ]

        output = "".join(chunks)
        self.assertIn("正在整理需求", output)
        self.assertIn("你好", output)


class CliCoverageTest(unittest.TestCase):
    def test_summary_task_done_success_and_failure(self) -> None:
        class SuccessfulTask:
            def result(self):
                return "ok"

        class FailingTask:
            def result(self):
                raise RuntimeError("summary failed")

        with patch("spec_agent.cli.logging.getLogger") as get_logger:
            logger = Mock()
            get_logger.return_value = logger
            _log_summary_task_done(SuccessfulTask())
            _log_summary_task_done(FailingTask())
            logger.exception.assert_called_once_with("后台摘要更新失败")

    def test_run_once_async_success(self) -> None:
        async def fake_astream(agent, message, config):
            yield "异步回复"
            return

        stdout = io.StringIO()
        with patch(
            "spec_agent.cli.astream_agent_replies",
            new=fake_astream,
        ), redirect_stdout(stdout):
            asyncio.run(_run_once(Mock(), "问题", demo=False))

        self.assertIn("异步回复", stdout.getvalue())

    def test_run_once_async_error(self) -> None:
        async def fake_astream(agent, message, config):
            if False:
                yield ""
            raise RuntimeError("stream failed")

        stdout = io.StringIO()
        with patch(
            "spec_agent.cli.astream_agent_replies",
            new=fake_astream,
        ), redirect_stdout(stdout):
            asyncio.run(_run_once(Mock(), "问题", demo=False))

        self.assertIn("运行出错", stdout.getvalue())
        self.assertIn("stream failed", stdout.getvalue())

    def test_run_once_async_no_output(self) -> None:
        async def fake_astream(agent, message, config):
            if False:
                yield ""

        stdout = io.StringIO()
        with patch(
            "spec_agent.cli.astream_agent_replies",
            new=fake_astream,
        ), redirect_stdout(stdout):
            asyncio.run(_run_once(Mock(), "问题", demo=False))

        self.assertIn("没有收到文本回复", stdout.getvalue())

    def test_run_non_demo_prompt_with_timing(self) -> None:
        calls = []

        async def fake_run_once(agent, question, *, demo):
            calls.append((agent, question, demo))

        with patch(
            "spec_agent.cli.load_settings",
            return_value=Settings(timing_enabled=True),
        ), patch(
            "spec_agent.cli.create_agent",
            return_value=Mock(),
        ), patch(
            "spec_agent.cli._run_once",
            new=fake_run_once,
        ), redirect_stdout(io.StringIO()):
            asyncio.run(
                _run(
                    prompt="一次性问题",
                    demo=False,
                    storage_path=None,
                    project_id="cli",
                )
            )

        self.assertEqual(len(calls), 1)

    def test_run_interactive_blank_and_exit(self) -> None:
        async def fake_run_once(agent, question, *, demo):
            return None

        with patch(
            "spec_agent.cli.load_settings",
            return_value=Settings(),
        ), patch(
            "spec_agent.cli.create_agent",
            return_value=Mock(),
        ), patch(
            "spec_agent.cli._run_once",
            new=fake_run_once,
        ), patch("builtins.input", side_effect=["", "quit"]):
            asyncio.run(
                _run(
                    prompt=None,
                    demo=False,
                    storage_path=None,
                    project_id="cli",
                )
            )

    def test_run_interactive_stops_on_eof(self) -> None:
        with patch(
            "spec_agent.cli.load_settings",
            return_value=Settings(),
        ), patch(
            "spec_agent.cli.create_agent",
            return_value=Mock(),
        ), patch("builtins.input", side_effect=EOFError):
            asyncio.run(
                _run(
                    prompt=None,
                    demo=False,
                    storage_path=None,
                    project_id="cli",
                )
            )

    def test_run_interactive_creates_summary_task(self) -> None:
        async def fake_run_once(agent, question, *, demo):
            return None

        def fake_to_thread(func, *args):
            return None

        task = Mock()
        with patch(
            "spec_agent.cli.load_settings",
            return_value=Settings(),
        ), patch(
            "spec_agent.cli.create_agent",
            return_value=Mock(),
        ), patch(
            "spec_agent.cli._run_once",
            new=fake_run_once,
        ), patch(
            "spec_agent.cli.asyncio.to_thread",
            new=fake_to_thread,
        ), patch(
            "spec_agent.cli.asyncio.create_task",
            return_value=task,
        ) as create_task, patch(
            "builtins.input",
            side_effect=["继续", "exit"],
        ):
            asyncio.run(
                _run(
                    prompt=None,
                    demo=False,
                    storage_path=None,
                    project_id="cli",
                )
            )

        create_task.assert_called_once()
        task.add_done_callback.assert_called_once_with(_log_summary_task_done)


class ConfigHelperCoverageTest(unittest.TestCase):
    def test_numeric_helpers_parse_and_fallback(self) -> None:
        self.assertEqual(_int({"value": "42"}, "value", default=None), 42)
        self.assertIsNone(_int({"value": "bad"}, "value", default=None))
        self.assertEqual(_int_required({"value": "7"}, "value", default=1), 7)
        self.assertEqual(_int_required({"value": "bad"}, "value", default=1), 1)
        self.assertEqual(_float({"value": "0.7"}, "value", default=0.1), 0.7)
        self.assertEqual(_float({"value": "bad"}, "value", default=0.1), 0.1)

    def test_bool_helper_parses_truthy_value(self) -> None:
        self.assertTrue(_bool({"value": "on"}, "value", default=False))


class LlmCoverageTest(unittest.TestCase):
    def test_enable_langsmith_tracing_sets_environment(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            enable_langsmith_tracing(
                Settings(
                    langsmith_tracing=True,
                    langsmith_api_key="secret-key",
                    langsmith_project="demo-project",
                )
            )

            self.assertEqual(os.environ["LANGCHAIN_TRACING_V2"], "true")
            self.assertEqual(os.environ["LANGCHAIN_API_KEY"], "secret-key")
            self.assertEqual(os.environ["LANGCHAIN_PROJECT"], "demo-project")

    def test_create_base_llm_requires_api_key(self) -> None:
        with patch(
            "spec_agent.llm.get_settings",
            return_value=Settings(api_key=None),
        ):
            with self.assertRaisesRegex(ValueError, "LLM_API_KEY"):
                create_base_llm()

    def test_create_base_llm_uses_explicit_base_url(self) -> None:
        with patch(
            "spec_agent.llm.get_settings",
            return_value=Settings(api_key="default-key"),
        ), patch("spec_agent.llm.ChatOpenAI") as chat_openai:
            create_base_llm(
                api_key="explicit-key",
                model_name="explicit-model",
                base_url="https://llm.example/v1",
            )

        kwargs = chat_openai.call_args.kwargs
        self.assertEqual(kwargs["api_key"], "explicit-key")
        self.assertEqual(kwargs["model"], "explicit-model")
        self.assertEqual(kwargs["base_url"], "https://llm.example/v1")


class MemoryHelperCoverageTest(unittest.TestCase):
    def test_message_index_after_last_match_and_missing(self) -> None:
        self.assertEqual(_message_index_after_last(["a", "b"], "b"), 2)
        self.assertIsNone(_message_index_after_last(["a", "b"], "missing"))

    def test_summarized_overflow_count_uses_stable_position(self) -> None:
        self.assertEqual(_summarized_overflow_count(3, 5, 4, 99), 2)
        self.assertEqual(_summarized_overflow_count(3, 5, None, 4), 3)


class MessageAndSanitizerCoverageTest(unittest.TestCase):
    def test_content_to_text_falls_back_to_str(self) -> None:
        self.assertEqual(content_to_text(3), "3")

    def test_tool_call_id_falls_back_to_object_attribute(self) -> None:
        self.assertEqual(
            _tool_call_id(SimpleNamespace(id="call_object")),
            "call_object",
        )


class RuntimeCoverageTest(unittest.TestCase):
    def test_runtime_delegates_graph_methods(self) -> None:
        graph = Mock()
        runtime = AgentRuntime(graph, Mock(), max_history_tokens=100)

        self.assertIs(runtime.astream("input"), graph.astream.return_value)
        self.assertIs(
            runtime.astream_events("input"),
            graph.astream_events.return_value,
        )
        self.assertIs(runtime.get_state({"config": 1}), graph.get_state.return_value)
        self.assertIs(
            runtime.update_state({"config": 1}, {"memory_summary": "x"}),
            graph.update_state.return_value,
        )

    def test_finalize_memory_returns_when_lock_is_busy(self) -> None:
        graph = Mock()
        runtime = AgentRuntime(graph, Mock(), max_history_tokens=100)

        runtime._summary_lock.acquire()
        runtime.finalize_memory({})
        runtime._summary_lock.release()

        graph.update_state.assert_not_called()

    def test_finalize_memory_returns_when_summary_is_recent(self) -> None:
        graph = Mock()
        runtime = AgentRuntime(graph, Mock(), max_history_tokens=100)
        runtime._last_summary_at = time.monotonic()

        runtime.finalize_memory({})

        graph.get_state.assert_not_called()
        graph.update_state.assert_not_called()


class SummarizerCoverageTest(unittest.TestCase):
    def test_merge_summaries_returns_existing_when_new_is_empty(self) -> None:
        self.assertEqual(merge_summaries("旧摘要", ""), "旧摘要")
        self.assertEqual(merge_summaries("", "新摘要"), "新摘要")


class TimingCoverageTest(unittest.TestCase):
    def test_phase_and_log_phase_when_enabled(self) -> None:
        with patch(
            "spec_agent.timing.get_settings",
            return_value=Settings(timing_enabled=True),
        ), patch.object(spec_agent.timing.TIMING_LOGGER, "info") as info:
            with phase("test_phase"):
                pass
            log_phase("test_log", time.perf_counter())

        self.assertGreaterEqual(info.call_count, 2)


class TokenizerCoverageTest(unittest.TestCase):
    def test_truncate_text_within_budget(self) -> None:
        self.assertEqual(truncate_text("hello", 100), "hello")

    def test_truncate_text_tail_edge_cases(self) -> None:
        self.assertEqual(truncate_text_tail("hello", 0), "")
        self.assertEqual(truncate_text_tail("hello", 100), "hello")
        self.assertEqual(truncate_text_tail("hello world", 1), "…")


class ExtractionCoverageTest(unittest.TestCase):
    def test_split_list_items(self) -> None:
        self.assertEqual(
            _split_list_items("Python，Vue 以及 Go"),
            ["Python", "Vue", "Go"],
        )

    def test_fast_extraction_returns_none_for_long_input(self) -> None:
        self.assertIsNone(_fast_extract_patch("x" * 81))

    def test_fast_extraction_supports_tech_stack_patterns(self) -> None:
        current = ProjectSpecification(tech_stack=["Vue"])
        tech_replaced = extract_specification_update(
            current,
            "技术栈是 Python 和 Go",
            RaisingLLM(),
        )
        build_with = extract_specification_update(
            ProjectSpecification(),
            "用 Python 和 FastAPI 开发",
            RaisingLLM(),
        )

        self.assertEqual(tech_replaced.tech_stack, ["Python", "Go"])
        self.assertEqual(build_with.tech_stack, ["Python", "FastAPI"])

    def test_parse_json_content_dict_model_fenced_and_fallback(self) -> None:
        class Dumpable(BaseModel):
            project_name: str = "dumpable"

        self.assertEqual(
            _parse_json_content({"project_name": "dict"}),
            {"project_name": "dict"},
        )
        self.assertEqual(
            _parse_json_content(Dumpable()),
            {"project_name": "dumpable"},
        )
        self.assertEqual(
            _parse_json_content('```json\n{"project_name": "fenced"}\n```'),
            {"project_name": "fenced"},
        )
        self.assertEqual(
            _parse_json_content('prefix {"project_name": "fallback",} suffix'),
            {"project_name": "fallback"},
        )

        with self.assertRaises(json.JSONDecodeError):
            _parse_json_content("no-json-here")

    def test_merge_specification_ignores_operation_fields_for_scalars(self) -> None:
        current = ProjectSpecification(project_name="保持原样")
        patch = SpecificationPatch(
            remove_items={"project_name": ["不该生效"]},
            replace_lists={"project_name": ["也不该生效"]},
        )

        merged = merge_specification(current, patch)

        self.assertEqual(merged.project_name, "保持原样")

    def test_coerce_patch_supports_patch_and_base_model(self) -> None:
        class DumpablePatch(BaseModel):
            project_name: str = "coerced"

        original = SpecificationPatch(project_name="original")

        self.assertIs(_coerce_patch(original), original)
        self.assertEqual(
            _coerce_patch(DumpablePatch()).project_name,
            "coerced",
        )

    def test_extract_blank_input_returns_current(self) -> None:
        current = ProjectSpecification(project_name="现有项目")

        self.assertIs(
            extract_specification_update(current, "  ", RaisingLLM()),
            current,
        )

    def test_extract_uses_structured_output_when_available(self) -> None:
        current = ProjectSpecification()
        patch = SpecificationPatch(project_name="结构化项目")

        updated = extract_specification_update(
            current,
            "这是一个需要 LLM 抽取的较长输入" * 3,
            StructuredPatchLLM(patch),
        )

        self.assertEqual(updated.project_name, "结构化项目")

    def test_extract_coerces_structured_base_model_result(self) -> None:
        class StructuredValue(BaseModel):
            project_name: str = "来自 BaseModel 的项目"

        updated = extract_specification_update(
            ProjectSpecification(),
            "这是一个需要 LLM 抽取的较长输入" * 3,
            StructuredBaseModelLLM(StructuredValue()),
        )

        self.assertEqual(updated.project_name, "来自 BaseModel 的项目")

    def test_extract_falls_back_to_original_after_retries(self) -> None:
        current = ProjectSpecification(project_name="保持项目")

        with patch("spec_agent.tools.extraction.time.sleep") as sleep:
            updated = extract_specification_update(
                current,
                "这是一个需要 LLM 抽取的较长输入" * 3,
                AlwaysFailingStructuredLLM(),
                max_retries=1,
            )

        self.assertIs(updated, current)
        sleep.assert_called_once_with(1)


class RegistryCoverageTest(unittest.TestCase):
    def test_extract_tool_returns_error_when_snapshot_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SpecificationStore(output_dir=tmp_dir)
            tools = build_specification_toolkit(
                store=store,
                llm=JsonPatchLLM(SpecificationPatch()),
            )

            with patch.object(store, "replace", side_effect=OSError("disk full")):
                payload = json.loads(
                    tools[0].invoke({"user_input": "项目叫会失败的项目"})
                )

        self.assertEqual(payload["status"], "error")
        self.assertIn("disk full", payload["message"])

    def test_extract_tool_falls_back_to_llm_for_long_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SpecificationStore(output_dir=tmp_dir)
            tools = build_specification_toolkit(
                store=store,
                llm=JsonPatchLLM(SpecificationPatch(project_name="长输入项目")),
            )

            payload = json.loads(
                tools[0].invoke(
                    {
                        "user_input": (
                            "请把项目名称确定为长输入项目，"
                            "这个描述足够长，因此不会走本地快速抽取。"
                        )
                        * 2
                    }
                )
            )

        self.assertEqual(payload["status"], "updated")
        self.assertEqual(store.get().project_name, "长输入项目")

    def test_check_tool_reports_complete_specification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SpecificationStore(output_dir=tmp_dir)
            store.replace(
                ProjectSpecification(
                    project_name="完整项目",
                    target_users=["产品经理"],
                    functional_requirements=["登录"],
                    non_functional_requirements=["支持 100 并发"],
                    constraints=["两周内上线"],
                    validation_specs=["登录通过验收"],
                )
            )
            tools = build_specification_toolkit(
                store=store,
                llm=JsonPatchLLM(SpecificationPatch()),
            )

            payload = json.loads(tools[1].invoke({}))

        self.assertTrue(payload["complete"])
        self.assertIn("所有必填字段已填写", payload["guidance"])

    def test_conflict_tool_reports_current_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SpecificationStore(output_dir=tmp_dir)
            store.replace(
                ProjectSpecification(
                    constraints=["预算有限"],
                    non_functional_requirements=["需要支持 10 万并发"],
                )
            )
            tools = build_specification_toolkit(
                store=store,
                llm=JsonPatchLLM(SpecificationPatch()),
            )

            payload = json.loads(tools[2].invoke({}))

        self.assertTrue(payload["has_conflicts"])
        self.assertTrue(any("低成本" in item["description"] for item in payload["conflicts"]))

    def test_render_tool_returns_rendered_path_for_complete_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SpecificationStore(output_dir=tmp_dir)
            store.replace(
                ProjectSpecification(
                    project_name="完整项目",
                    target_users=["产品经理"],
                    functional_requirements=["登录"],
                    non_functional_requirements=["支持 100 并发"],
                    constraints=["两周内上线"],
                    validation_specs=["登录通过验收"],
                )
            )
            tools = build_specification_toolkit(
                store=store,
                llm=JsonPatchLLM(SpecificationPatch()),
            )

            payload = json.loads(
                tools[3].invoke(
                    {
                        "output_format": "markdown",
                        "output_dir": tmp_dir,
                    }
                )
            )

            self.assertEqual(payload["status"], "rendered")
            self.assertTrue((Path(tmp_dir) / "specification.md").exists())


class RenderingImportErrorTest(unittest.TestCase):
    def test_render_docx_raises_friendly_error_without_python_docx(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("builtins.__import__", side_effect=ImportError):
                with self.assertRaisesRegex(RuntimeError, "python-docx"):
                    render_docx(ProjectSpecification(), tmp_dir)


class StoreCoverageTest(unittest.TestCase):
    def test_load_or_default_raises_for_invalid_specification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_path = Path(tmp_dir) / "invalid.json"
            storage_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project_id": "invalid",
                        "specification": "not-a-valid-specification",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "规格文件内容无效"):
                SpecificationStore(storage_path=storage_path)

    def test_snapshot_path_uses_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SpecificationStore(output_dir=tmp_dir)

            self.assertEqual(
                store.snapshot_path("custom.md"),
                Path(tmp_dir) / "custom.md",
            )


if __name__ == "__main__":
    unittest.main()
