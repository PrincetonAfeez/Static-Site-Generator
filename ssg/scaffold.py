from __future__ import annotations

from datetime import date
from pathlib import Path

from .errors import CLIError
from .models import SiteConfig
from .page_builder import slugify


def scaffold_content(config: SiteConfig, relative_target: str, title: str | None = None) -> Path:
    target = Path(relative_target)
    if target.is_absolute():
        raise CLIError("new content path must be relative")
    if target.suffix.lower() not in {"", ".md", ".markdown"}:
        raise CLIError("new content path must be a Markdown file")
    if not target.suffix:
        target = target.with_suffix(".md")

    full_path = (config.content_dir / target).resolve()
    try:
        full_path.relative_to(config.content_dir.resolve())
    except ValueError as exc:
        raise CLIError("new content path must stay inside content_dir") from exc
    if full_path.exists():
        raise CLIError("content file already exists", path=full_path)

    page_title = title or title_from_path(target)
    slug = slugify(target.stem)
    is_post = any(part in config.post_collections for part in target.parts)
    layout_line = "layout: post.html" if is_post else "layout: page.html"
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(
        "\n".join(
            [
                "---",
                f"title: {quote_frontmatter(page_title)}",
                f"date: {date.today().isoformat()}",
                "tags: ",
                layout_line,
                "draft: true",
                f"slug: {quote_frontmatter(slug)}",
                "description: ",
                "author: ",
                "---",
                "",
                f"# {page_title}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return full_path


def quote_frontmatter(value: str) -> str:
    if not value:
        return '""'
    if any(char in value for char in ':\n\r"#\'') or value[0] in "- ":
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def title_from_path(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()
