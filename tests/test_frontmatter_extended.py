""" Test Frontmatter Extended """

from __future__ import annotations

from pathlib import Path

import pytest

from ssg.errors import FrontMatterError
from ssg.frontmatter import (
    _normalize_tag,
    _unescape_double_quoted,
    _unescape_single_quoted,
    _unquote,
    normalize_date,
    normalize_tags,
    parse_yaml_metadata,
    split_frontmatter,
)
from ssg.models import SourceFile


def source_for(path, root):
    return SourceFile(path=path, relative_path=path.relative_to(root), extension=path.suffix)


def test_split_frontmatter_missing_closing_delimiter(site_root):
    source = source_for(site_root / "content" / "open.md", site_root / "content")
    text = "---\ntitle: Open\n# Body\n"

    with pytest.raises(FrontMatterError, match="closing"):
        split_frontmatter(text, source, [])


def test_parse_yaml_metadata_skips_blank_lines(site_root):
    source = source_for(site_root / "content" / "meta.md", site_root / "content")
    metadata = parse_yaml_metadata("\ntitle: Hello\n\ndraft: true\n", source, [])

    assert metadata["title"] == "Hello"
    assert metadata["draft"] is True


def test_parse_yaml_metadata_rejects_non_mapping(site_root):
    source = source_for(site_root / "content" / "meta.md", site_root / "content")

    with pytest.raises(FrontMatterError, match="mapping"):
        parse_yaml_metadata("- item\n", source, [])


def test_parse_yaml_metadata_rejects_invalid_yaml(site_root):
    source = source_for(site_root / "content" / "meta.md", site_root / "content")

    with pytest.raises(FrontMatterError, match="invalid YAML"):
        parse_yaml_metadata("title: [unclosed", source, [])


def test_normalize_tags_empty_string():
    source = SourceFile(path=Path("x.md"), relative_path=Path("x.md"), extension=".md")

    assert normalize_tags("", source, 1) == []


def test_normalize_date_invalid():
    source = SourceFile(path=Path("x.md"), relative_path=Path("x.md"), extension=".md")

    with pytest.raises(FrontMatterError, match="invalid date"):
        normalize_date("not-a-date", source, 1)


def test_unquote_passthrough():
    assert _unquote("plain") == "plain"


def test_unescape_single_quoted_trailing_backslash():
    assert _unescape_single_quoted("ok\\") == "ok\\"


def test_unescape_single_quoted_unknown_escape():
    assert _unescape_single_quoted("a\\z") == "a\\z"


def test_unescape_double_quoted_trailing_backslash():
    assert _unescape_double_quoted("ok\\") == "ok\\"


def test_unescape_double_quoted_unknown_escape():
    assert _unescape_double_quoted("a\\z") == "a\\z"


def test_normalize_tag_strips_and_lowers():
    assert _normalize_tag("  Python  ") == "python"


def test_normalize_tags_skip_empty_segments(site_root):
    source = source_for(site_root / "content" / "meta.md", site_root / "content")

    assert normalize_tags("python, , docs", source, 1) == ["python", "docs"]
