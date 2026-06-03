""" Test Frontmatter """

from __future__ import annotations

import pytest

from ssg.errors import FrontMatterError
from ssg.frontmatter import parse_document, parse_yaml_metadata
from ssg.models import SourceFile


def source_for(path, root):
    return SourceFile(path=path, relative_path=path.relative_to(root), extension=path.suffix)


def test_frontmatter_parses_supported_fields(site_root):
    path = site_root / "content" / "blog" / "first.md"
    document = parse_document(source_for(path, site_root / "content"))

    assert document.metadata["title"] == "First"
    assert document.metadata["tags"] == ["python", "static-sites"]
    assert document.metadata["draft"] is False
    assert document.metadata["date"] == "2026-05-26"
    assert "# First" in document.body_markdown


def test_frontmatter_allows_missing_block(site_root):
    path = site_root / "content" / "plain.md"
    path.write_text("# Plain\n", encoding="utf-8")

    document = parse_document(source_for(path, site_root / "content"))

    assert document.metadata == {}
    assert document.body_markdown == "# Plain\n"


def test_frontmatter_reports_line_for_bad_boolean(site_root):
    path = site_root / "content" / "bad.md"
    path.write_text("---\ntitle: Bad\ndraft: maybe\n---\n", encoding="utf-8")

    with pytest.raises(FrontMatterError) as error:
        parse_document(source_for(path, site_root / "content"))

    assert error.value.line == 2


def test_frontmatter_warns_on_unknown_field(site_root):
    path = site_root / "content" / "unknown.md"
    path.write_text("---\ntitle: Page\nunknown_field: hello\n---\n# Page\n", encoding="utf-8")

    document = parse_document(source_for(path, site_root / "content"))

    assert any("unknown_field" in warning for warning in document.warnings)
    assert document.metadata["unknown_field"] == "hello"


def test_frontmatter_parses_yaml_quoted_values(site_root):
    source = source_for(site_root / "content" / "quoted.md", site_root / "content")
    metadata = parse_yaml_metadata('title: "My Post: \\"Special\\" Edition"', source, [])

    assert metadata["title"] == 'My Post: "Special" Edition'


def test_frontmatter_parses_yaml_list_tags(site_root):
    source = source_for(site_root / "content" / "tags.md", site_root / "content")
    metadata = parse_yaml_metadata("tags:\n  - python\n  - docs", source, [])

    assert metadata["tags"] == ["python", "docs"]


def test_frontmatter_accepts_yes_no_for_draft(site_root):
    source = source_for(site_root / "content" / "draft.md", site_root / "content")
    metadata = parse_yaml_metadata("draft: yes", source, [])

    assert metadata["draft"] is True
