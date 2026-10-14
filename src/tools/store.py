"""规格对象的内存存储。"""

from __future__ import annotations

from pathlib import Path

from .schemas import ProjectSpecification


class SpecificationStore:
    """保存当前会话的规格对象和输出目录。

    存储仅存在于当前进程，符合项目现在要求的短期记忆策略。
    """

    def __init__(
        self,
        specification: ProjectSpecification | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self._specification = specification or ProjectSpecification()
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "output"

    def get(self) -> ProjectSpecification:
        return self._specification

    def replace(self, specification: ProjectSpecification) -> None:
        self._specification = specification

    def snapshot_path(self, filename: str = "specification.md") -> Path:
        return self.output_dir / filename
