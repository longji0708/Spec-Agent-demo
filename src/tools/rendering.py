"""使用 Jinja2 渲染规格定义文档。"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .schemas import ProjectSpecification

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(enabled_extensions=("html",)),
    trim_blocks=True,
    lstrip_blocks=True,
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
    template = _ENV.get_template("specification.md.j2")
    content = template.render(spec=specification)
    output_path = _ensure_output_dir(output_dir) / filename
    output_path.write_text(content, encoding="utf-8")
    return output_path


def render_html(
    specification: ProjectSpecification,
    output_dir: str | Path,
    filename: str = "specification.html",
) -> Path:
    template = _ENV.get_template("specification.html.j2")
    content = template.render(spec=specification)
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

    sections = {
        "目标用户": specification.target_users,
        "功能需求": specification.functional_requirements,
        "非功能需求": specification.non_functional_requirements,
        "约束条件": specification.constraints,
        "交付物": specification.deliverables,
        "验证规格": specification.validation_specs,
        "技术栈": specification.tech_stack,
        "风险": specification.risks,
    }

    for heading, items in sections.items():
        document.add_heading(heading, level=1)
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

    if normalized_format in {"markdown", "md"}:
        return render_markdown(specification, output_dir)
    if normalized_format in {"html", "htm"}:
        return render_html(specification, output_dir)
    if normalized_format in {"word", "docx"}:
        return render_docx(specification, output_dir)

    raise ValueError(
        f"不支持的输出格式：{output_format}，可选值为 markdown、html、word。"
    )
