from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .errors import PageBuildError
from .models import Page, ParsedDocument, SiteConfig


SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def build_page(document: ParsedDocument, body_html: str, config: SiteConfig) -> Page:
    metadata = document.metadata
    relative_path = document.source.relative_path

    raw_slug = metadata.get("slug")
    if raw_slug is not None:
        raw_slug_str = str(raw_slug)
        if ".." in raw_slug_str or "/" in raw_slug_str or "\\" in raw_slug_str:
            raise PageBuildError(
                f'slug contains path traversal: "{raw_slug_str}"',
                path=document.source.path,
            )

    slug = slugify(str(raw_slug or relative_path.stem))
    if not slug:
        raise PageBuildError("could not derive slug", path=document.source.path)

    url = derive_url(relative_path, slug, config.permalink)
    output_path = output_path_for_url(config.output_dir, url)

    return Page(
        source_path=document.source.path,
        relative_source_path=relative_path,
        title=derive_title(relative_path, metadata),
        slug=slug,
        url=url,
        output_path=output_path,
        layout=str(metadata.get("layout") or config.default_layout),
        date=_optional_string(metadata.get("date")),
        tags=list(metadata.get("tags") or []),
        draft=bool(metadata.get("draft", False)),
        body_html=body_html,
        metadata=dict(metadata),
        collection=derive_collection(relative_path),
        generated=False,
    )


def derive_url(relative_path: Path, slug: str, permalink: str = "/{path}/{slug}/") -> str:
    parent_parts = [slugify(part) for part in relative_path.parent.parts if part not in {"", "."}]
    if relative_path.stem.lower() == "index":
        # Index pages collapse to the directory URL; the permalink template
        # only applies to non-index content.
        if not parent_parts:
            return "/"
        return "/" + "/".join(parent_parts) + "/"

    path_segment = "/".join(parent_parts)
    url = permalink.replace("{path}", path_segment).replace("{slug}", slug)
    return _normalize_url(url)


def _normalize_url(url: str) -> str:
    if not url.startswith("/"):
        url = "/" + url
    while "//" in url:
        url = url.replace("//", "/")
    if not url.endswith("/"):
        url = url + "/"
    return url


def output_path_for_url(output_dir: Path, url: str) -> Path:
    clean_url = url.strip("/")
    if not clean_url:
        return output_dir / "index.html"
    return output_dir.joinpath(*clean_url.split("/")) / "index.html"


def derive_title(relative_path: Path, metadata: dict[str, Any]) -> str:
    title = metadata.get("title")
    if title:
        return str(title)
    if relative_path.stem.lower() == "index":
        if relative_path.parent == Path("."):
            return "Home"
        return relative_path.parent.name.replace("-", " ").replace("_", " ").title()
    return relative_path.stem.replace("-", " ").replace("_", " ").title()


def derive_collection(relative_path: Path) -> str | None:
    parts = [part for part in relative_path.parent.parts if part not in {"", "."}]
    if not parts:
        return None
    return slugify(parts[0])


def warn_collection_slug_collisions(pages: list[Page], warnings: list[str]) -> None:
    seen: dict[str, str] = {}
    for page in pages:
        if page.relative_source_path is None:
            continue
        parts = [
            part
            for part in page.relative_source_path.parent.parts
            if part not in {"", "."}
        ]
        if not parts:
            continue
        raw_name = parts[0]
        slug = slugify(raw_name)
        previous = seen.get(slug)
        if previous is not None and previous != raw_name:
            message = (
                f"collection directories '{previous}' and '{raw_name}' "
                f"both map to collection '{slug}'"
            )
            if message not in warnings:
                warnings.append(message)
        seen.setdefault(slug, raw_name)


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    slug = SLUG_PATTERN.sub("-", lowered).strip("-")
    return slug


def _optional_string(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    return str(value)
