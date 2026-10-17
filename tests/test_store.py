import tempfile
import unittest
from pathlib import Path

from spec_agent.tools.schemas import ProjectSpecification
from spec_agent.tools.store import SpecificationStore


class SpecificationStorePersistenceTest(unittest.TestCase):
    def test_saves_and_loads_specification_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_path = Path(tmp_dir) / "specification.json"
            store = SpecificationStore(storage_path=storage_path)
            store.replace(
                ProjectSpecification(
                    project_name="持久化项目",
                    functional_requirements=["登录"],
                )
            )

            restored = SpecificationStore.load(storage_path).get()

            self.assertTrue(storage_path.exists())
            self.assertEqual(restored.project_name, "持久化项目")
            self.assertEqual(restored.functional_requirements, ["登录"])

    def test_project_id_isolates_output_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            first = SpecificationStore(
                storage_path=Path(tmp_dir) / "a.json",
                project_id="a",
            )
            second = SpecificationStore(
                storage_path=Path(tmp_dir) / "b.json",
                project_id="b",
            )

            self.assertEqual(first.output_dir, Path(tmp_dir) / "a")
            self.assertEqual(second.output_dir, Path(tmp_dir) / "b")


if __name__ == "__main__":
    unittest.main()
