""" Static Site Generator Models """

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SiteConfig:
    root_dir: Path
    title: str
    base_url: str
    content_dir: Path
    layout_dir: Path
    partial_dir: Path
    static_dir: Path
    output_dir: Path
    default_layout: str
    permalink: str
    include_drafts: bool = False
    clean_output: bool = True
    incremental: bool = False
    generate_sitemap: bool = True
    post_collections: tuple[str, ...] = ()
    assets_dir: str = "assets"


@dataclass(frozen=True)
class SourceFile:
    path: Path
    relative_path: Path
    extension: str


@dataclass
class ParsedDocument:
    source: SourceFile
    metadata: dict[str, Any]
    body_markdown: str
    raw_text: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class Page:
    source_path: Path | None
    relative_source_path: Path | None
    title: str
    slug: str
    url: str
    output_path: Path
    layout: str
    date: str | None
    tags: list[str]
    draft: bool
    body_html: str
    metadata: dict[str, Any] = field(default_factory=dict)
    collection: str | None = None
    generated: bool = False
    previous_url: str | None = None
    next_url: str | None = None


@dataclass
class NavNode:
    title: str
    url: str | None = None
    children: dict[str, "NavNode"] = field(default_factory=dict)


@dataclass
class SiteModel:
    config: SiteConfig
    pages: list[Page]
    pages_by_url: dict[str, Page]
    tags: dict[str, list[Page]]
    collections: dict[str, list[Page]]
    nav_tree: NavNode
    build_time: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class RenderedPage:
    page: Page
    html: str


@dataclass(frozen=True, eq=False)
class BuildManifest:
    schema_version: int
    started_at: str
    finished_at: str
    elapsed_seconds: float
    pages_discovered: int
    pages_rendered: int
    drafts_skipped: int
    pages_failed: int
    generated_pages: int
    assets_copied: int
    warnings: list[str]
    errors: list[str]
    output_files: list[str]
    incremental: bool = False
    stale_files_removed: int = 0


@dataclass(frozen=True, eq=False)
class BuildResult:
    config: SiteConfig
    site: SiteModel
    manifest: BuildManifest
    rendered_pages: list[RenderedPage]
    asset_files: list[Path]
