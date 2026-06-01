from __future__ import annotations

import pytest

from ssg.config import load_config
from ssg.errors import CLIError
from ssg.scaffold import scaffold_content


def test_scaffold_creates_markdown_file(site_root):
    config = load_config(site_root / "site.toml")
    path = scaffold_content(config, "guides/new-page", title="New Page")

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "title: New Page" in text
    assert "draft: true" in text


def test_scaffold_rejects_absolute_path(site_root):
    config = load_config(site_root / "site.toml")

    with pytest.raises(CLIError, match="relative"):
        scaffold_content(config, r"C:\outside\post.md")


def test_scaffold_rejects_path_outside_content_dir(site_root):
    config = load_config(site_root / "site.toml")

    with pytest.raises(CLIError, match="inside content_dir"):
        scaffold_content(config, "../escape.md")


def test_scaffold_rejects_existing_file(site_root):
    config = load_config(site_root / "site.toml")

    with pytest.raises(CLIError, match="already exists"):
        scaffold_content(config, "about.md")


def test_scaffold_rejects_non_markdown_extension(site_root):
    config = load_config(site_root / "site.toml")

    with pytest.raises(CLIError, match="Markdown"):
        scaffold_content(config, "notes.txt")
