""" Static Site Generator Discovery """

from __future__ import annotations

from pathlib import Path

from .errors import DiscoveryError
from .models import SiteConfig, SourceFile


MARKDOWN_EXTENSIONS = {".md", ".markdown"}


def discover_content(config: SiteConfig) -> list[SourceFile]:
    content_dir = config.content_dir
    if not content_dir.exists():
        raise DiscoveryError("content directory not found", path=content_dir)

    sources: list[SourceFile] = []
    for path in content_dir.rglob("*"):
        relative = path.relative_to(content_dir)
        if _has_hidden_part(relative):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in MARKDOWN_EXTENSIONS:
            continue
        sources.append(
            SourceFile(
                path=path,
                relative_path=relative,
                extension=path.suffix.lower(),
            )
        )

    return sorted(sources, key=lambda source: source.relative_path.as_posix())


def _has_hidden_part(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)
