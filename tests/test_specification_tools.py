import json
import tempfile
import unittest
from pathlib import Path

from langchain_core.messages import AIMessage

from src.tools.conflicts import detect_conflicts
from src.tools.extraction import (
    extract_specification_update,
    merge_specification,
    should_extract_specification,
)
from src.tools.registry import build_specification_toolkit
from src.tools.rendering import render_docx, render_html, render_markdown
from src.tools.schemas import ProjectSpecification, SpecificationPatch
from src.tools.store import SpecificationStore
from src.tools.validation import check_missing_fields


class FakeLLM:
    def __init__(self, patch: SpecificationPatch) -> None:
        self._patch = patch

    def invoke(self, messages):
        return AIMessage(content=self._patch.model_dump_json(exclude_none=True))


class SpecificationMergeTest(unittest.TestCase):
    def test_skips_short_acknowledgement(self) -> None:
        self.assertFalse(should_extract_specification("好的"))
        self.assertTrue(should_extract_specification("希望生成 md 文档"))

    def test_merge_keeps_old_items_and_appends_new_items(self) -> None:
        current = ProjectSpecification(
            project_name="旧项目",
            functional_requirements=["登录"],
        )
        patch = SpecificationPatch(
            functional_requirements=["登录", "导出报告"],
            tech_stack=["Python"],
        )

        merged = merge_specification(current, patch)

        self.assertEqual(merged.project_name, "旧项目")
        self.assertEqual(merged.functional_requirements, ["登录", "导出报告"])
        self.assertEqual(merged.tech_stack, ["Python"])

    def test_extract_specification_update_uses_llm_output(self) -> None:
        patch = SpecificationPatch(
            project_name="示例项目",
            target_users=["产品经理"],
        )

        updated = extract_specification_update(
            ProjectSpecification(),
            "这是一个给产品经理用的示例项目",
            FakeLLM(patch),
        )

        self.assertEqual(updated.project_name, "示例项目")
        self.assertEqual(updated.target_users, ["产品经理"])


class ValidationTest(unittest.TestCase):
    def test_missing_fields_includes_performance_hint(self) -> None:
        specification = ProjectSpecification(
            project_name="示例",
            target_users=["用户"],
            functional_requirements=["登录"],
            non_functional_requirements=["系统需要稳定"],
        )

        missing = check_missing_fields(specification)
        fields = {item.field for item in missing}

        self.assertIn("non_functional_requirements.performance", fields)
        self.assertTrue(
            any("并发用户数" in item.follow_up for item in missing)
        )


class ConflictTest(unittest.TestCase):
    def test_detects_cost_and_offline_conflicts(self) -> None:
        specification = ProjectSpecification(
            constraints=["预算有限"],
            non_functional_requirements=[
                "需要支持 10 万并发",
                "离线也能使用",
                "同时要求云端实时同步",
            ],
        )

        conflicts = detect_conflicts(specification)
        codes = {item.code for item in conflicts}

        self.assertIn("low_cost_vs_high_concurrency", codes)
        self.assertIn("offline_vs_realtime_sync", codes)


class RenderingTest(unittest.TestCase):
    def test_render_markdown_and_html(self) -> None:
        specification = ProjectSpecification(
            project_name="示例项目",
            target_users=["产品经理"],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            markdown_path = render_markdown(specification, tmp_dir)
            html_path = render_html(specification, tmp_dir)
            docx_path = render_docx(specification, tmp_dir)

            self.assertEqual(Path(markdown_path).name, "specification.md")
            self.assertEqual(Path(html_path).name, "specification.html")
            self.assertEqual(Path(docx_path).name, "specification.docx")
            self.assertIn("示例项目", Path(markdown_path).read_text(encoding="utf-8"))
            self.assertIn("示例项目", Path(html_path).read_text(encoding="utf-8"))
            self.assertTrue(docx_path.exists())


class SpecificationToolkitTest(unittest.TestCase):
    def test_extract_tool_updates_store_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SpecificationStore(output_dir=tmp_dir)
            fake_llm = FakeLLM(
                SpecificationPatch(project_name="示例项目")
            )
            tools = build_specification_toolkit(store=store, llm=fake_llm)
            extract_tool = tools[0]

            result = extract_tool.invoke({"user_input": "项目叫示例项目"})
            payload = json.loads(result)
            check_tool = tools[1]
            check_payload = json.loads(check_tool.invoke({}))

            self.assertEqual(store.get().project_name, "示例项目")
            self.assertEqual(payload["status"], "updated")
            self.assertTrue((Path(tmp_dir) / "specification.md").exists())
            self.assertFalse(check_payload["complete"])


if __name__ == "__main__":
    unittest.main()
