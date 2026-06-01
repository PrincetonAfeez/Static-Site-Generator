from __future__ import annotations

import dataclasses

import pytest

from ssg.config import load_config
from ssg.discovery import discover_content
from ssg.errors import DiscoveryError


def test_discovery_finds_markdown_and_skips_hidden(site_root):
    (site_root / "content" / ".hidden.md").write_text("# hidden", encoding="utf-8")
    (site_root / "content" / ".hidden-dir").mkdir()
    (site_root / "content" / ".hidden-dir" / "page.md").write_text("# hidden", encoding="utf-8")
    (site_root / "content" / "notes.txt").write_text("ignore", encoding="utf-8")

    config = load_config(site_root / "site.toml")
    sources = discover_content(config)

    assert [source.relative_path.as_posix() for source in sources] == [
        "about.md",
        "blog/draft.md",
        "blog/first.md",
        "index.md",
    ]


def test_discovery_raises_when_content_dir_missing(site_root):
    config = load_config(site_root / "site.toml")
    config = dataclasses.replace(config, content_dir=site_root / "gone")

    with pytest.raises(DiscoveryError, match="content directory not found"):
        discover_content(config)
