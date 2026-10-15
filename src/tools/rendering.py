"""使用 Jinja2 渲染规格定义文档。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .schemas import ProjectSpecification


@dataclass(frozen=True)
class SectionConfig:
    key: str
    title: str


SPECIFICATION_SECTIONS: tuple[SectionConfig, ...] = (
    SectionConfig(key="target_users", title="目标用户"),
    SectionConfig(key="functional_requirements", title="功能需求"),
    SectionConfig(key="non_functional_requirements", title="非功能需求"),
    SectionConfig(key="constraints", title="约束条件"),
    SectionConfig(key="deliverables", title="交付物"),
    SectionConfig(key="validation_specs", title="验证规格"),
    SectionConfig(key="tech_stack", title="技术栈"),
    SectionConfig(key="risks", title="风险"),
)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_COMMON_ENV_OPTIONS = {
    "loader": FileSystemLoader(str(_TEMPLATE_DIR)),
    "trim_blocks": True,
    "lstrip_blocks": True,
}
_MD_ENV = Environment(autoescape=False, **_COMMON_ENV_OPTIONS)
_HTML_ENV = Environment(
    autoescape=True,
    **_COMMON_ENV_OPTIONS,
)

def _ensure_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_markdown(
    specification: ProjectSpecification,
    output_dir: str | Path,
    filename: str = "specification.md",
) -> Path:
    template = _MD_ENV.get_template("specification.md.j2")
    content = template.render(
        spec=specification,
        sections=SPECIFICATION_SECTIONS,
    )
    output_path = _ensure_output_dir(output_dir) / filename
    output_path.write_text(content, encoding="utf-8")
    return output_path


def render_html(
    specification: ProjectSpecification,
    output_dir: str | Path,
    filename: str = "specification.html",
) -> Path:
    template = _HTML_ENV.get_template("specification.html.j2")
    content = template.render(
        spec=specification,
        sections=SPECIFICATION_SECTIONS,
    )
    output_path = _ensure_output_dir(output_dir) / filename
    output_path.write_text(content, encoding="utf-8")
    return output_path


def render_docx(
    specification: ProjectSpecification,
    output_dir: str | Path,
    filename: str = "specification.docx",
) -> Path:
    """使用 python-docx 生成 Word 文档。"""
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError(
            "生成 Word 文档需要安装 python-docx，请执行 pip install python-docx。"
        ) from exc

    document = Document()
    title = specification.project_name or "项目规格定义书"
    document.add_heading(title, level=0)

    for section in SPECIFICATION_SECTIONS:
        items = getattr(specification, section.key)
        document.add_heading(section.title, level=1)
        if items:
            for item in items:
                document.add_paragraph(item, style="List Bullet")
        else:
            document.add_paragraph("待补充")

    output_path = _ensure_output_dir(output_dir) / filename
    document.save(output_path)
    return output_path


def render_specification(
    specification: ProjectSpecification,
    output_dir: str | Path,
    output_format: str,
) -> Path:
    """按格式渲染规格定义文档。"""
    normalized_format = output_format.lower().strip()
    renderer = _RENDERERS.get(normalized_format)
    if renderer is None:
        raise ValueError(
            f"不支持的输出格式：{output_format}，可选值为 markdown、html、word。"
        )

    return renderer(specification, output_dir)


_RENDERERS = {
    "markdown": render_markdown,
    "md": render_markdown,
    "html": render_html,
    "htm": render_html,
    "word": render_docx,
    "docx": render_docx,
}
