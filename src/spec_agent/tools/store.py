"""规格对象的存储与轻量 JSON 持久化。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .schemas import ProjectSpecification


class SpecificationStore:
    """保存当前会话的规格对象和输出目录。

    不配置 ``storage_path`` 时保持内存态，适合测试和一次性 CLI 会话；配置后
    每次 ``replace()`` 都会同步写入 JSON，可用于恢复未完成的需求讨论。
    """

    def __init__(
        self,
        specification: ProjectSpecification | None = None,
        output_dir: str | Path | None = None,
        storage_path: str | Path | None = None,
        project_id: str = "default",
        auto_save: bool = True,
    ) -> None:
        self.project_id = project_id
        self.auto_save = auto_save
        self.storage_path = Path(storage_path) if storage_path else None
        if output_dir is not None:
            self.output_dir = Path(output_dir)
        elif self.storage_path is not None:
            self.output_dir = self.storage_path.parent / self.project_id
        else:
            self.output_dir = Path.cwd() / "output" / self.project_id
        self._specification = (
            specification if specification is not None else self._load_or_default()
        )
        if auto_save and self.storage_path is not None:
            self.save()

    def get(self) -> ProjectSpecification:
        return self._specification

    def replace(self, specification: ProjectSpecification) -> None:
        self._specification = specification
        if self.auto_save:
            self.save()

    def save(self) -> None:
        if self.storage_path is None:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "project_id": self.project_id,
            "specification": json.loads(self._specification.model_dump_json()),
        }
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.storage_path.parent,
            prefix=f".{self.storage_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp_file:
            tmp_file.write(json.dumps(payload, ensure_ascii=False, indent=2))
            tmp_path = Path(tmp_file.name)
        os.replace(tmp_path, self.storage_path)

    @classmethod
    def load(
        cls,
        storage_path: str | Path,
        project_id: str | None = None,
    ) -> SpecificationStore:
        """从已有的 ``specification.json`` 恢复规格对象。

        优先使用 JSON 中保存的 ``project_id``；需要迁移或覆盖时，可显式传入
        ``project_id``。
        """
        path = Path(storage_path)
        payload = cls._read_payload(path)
        saved_project_id = payload.get("project_id")
        resolved_project_id = (
            project_id
            or (saved_project_id if isinstance(saved_project_id, str) else path.stem)
            or path.stem
        )
        return cls(
            storage_path=path,
            project_id=resolved_project_id,
        )

    def _load_or_default(self) -> ProjectSpecification:
        if self.storage_path is None or not self.storage_path.exists():
            return ProjectSpecification()
        payload = self._read_payload(self.storage_path)
        specification_data = (
            payload.get("specification")
            if isinstance(payload, dict) and "specification" in payload
            else payload
        )
        try:
            return ProjectSpecification.model_validate(specification_data)
        except ValueError as exc:
            raise ValueError(f"规格文件内容无效：{self.storage_path}") from exc

    @staticmethod
    def _read_payload(path: Path) -> dict[str, object]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"无法读取规格文件：{path}") from exc
        return payload if isinstance(payload, dict) else {}

    def snapshot_path(self, filename: str = "specification.md") -> Path:
        return self.output_dir / filename
