import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from spec_agent.cli import main


class CliEntryPointTest(unittest.TestCase):
    def test_demo_prompt_creates_storage_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_path = Path(tmp_dir) / "demo.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                main(
                    [
                        "--demo",
                        "--prompt",
                        "演示项目",
                        "--storage",
                        str(storage_path),
                        "--project",
                        "demo",
                    ]
                )

            output = stdout.getvalue()
            self.assertTrue(storage_path.exists())
            self.assertTrue((Path(tmp_dir) / "demo" / "specification.md").exists())
            self.assertIn("演示", output)

    def test_invalid_storage_file_raises_friendly_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_path = Path(tmp_dir) / "broken.json"
            storage_path.write_text("{not-json", encoding="utf-8")

            with self.assertRaises(ValueError):
                main(
                    [
                        "--demo",
                        "--prompt",
                        "演示项目",
                        "--storage",
                        str(storage_path),
                        "--project",
                        "broken",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
