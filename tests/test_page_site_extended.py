""" Test Page Site Extended """

from __future__ import annotations

from pathlib import Path

import pytest

from ssg.config import load_config
from ssg.models import NavNode, Page
from ssg.page_builder import (
    _normalize_url,
    _optional_string,
    derive_collection,
    derive_title,
    output_path_for_url,
    slugify,
)
from ssg.page_builder import build_page, derive_url
from ssg.frontmatter import parse_document
from ssg.markdown_adapter import MarkdownConverter
from ssg.models import SourceFile
from ssg.site_model import (
    _source_label,
    dedupe_pages_by_url,
    render_nav_html,
)


def test_slugify_empty_after_strip():
    assert slugify("---") == ""


def test_normalize_url_adds_leading_and_trailing_slash():
    assert _normalize_url("blog/post") == "/blog/post/"


def test_normalize_url_collapses_double_slashes():
    assert _normalize_url("//blog//post//") == "/blog/post/"


def test_derive_title_index_in_subdirectory():
    title = derive_title(Path("guides/index.md"), {})

    assert title == "Guides"


def test_derive_title_from_filename():
    assert derive_title(Path("my-page.md"), {}) == "My Page"


def test_derive_collection_root_file():
    assert derive_collection(Path("page.md")) is None


def test_optional_string_empty():
    assert _optional_string("") is None
    assert _optional_string(None) is None
    assert _optional_string("x") == "x"


def test_output_path_root():
    assert output_path_for_url(Path("dist"), "/") == Path("dist") / "index.html"


def test_build_page_rejects_empty_slug(site_root):
    path = site_root / "content" / "!!!.md"
    path.write_text("---\ntitle: Bad\n---\n# Bad\n", encoding="utf-8")
    config = load_config(site_root / "site.toml")
    source = SourceFile(
        path=path, relative_path=path.relative_to(site_root / "content"), extension=".md"
    )
    document = parse_document(source)
    html = MarkdownConverter().convert(document.body_markdown)

    from ssg.errors import PageBuildError

    with pytest.raises(PageBuildError, match="could not derive slug"):
        build_page(document, html, config)


def test_derive_url_nested_index():
    url = derive_url(Path("docs/index.md"), "index", permalink="/{path}/{slug}/")

    assert url == "/docs/"


def test_dedupe_pages_by_url_skips_later_duplicate(site_root):
    config = load_config(site_root / "site.toml")
    first = Page(
        source_path=config.content_dir / "a.md",
        relative_source_path=Path("a.md"),
        title="A",
        slug="a",
        url="/dup/",
        output_path=output_path_for_url(config.output_dir, "/dup/"),
        layout="page.html",
        date=None,
        tags=[],
        draft=False,
        body_html="",
    )
    second = Page(
        source_path=config.content_dir / "b.md",
        relative_source_path=Path("b.md"),
        title="B",
        slug="b",
        url="/dup/",
        output_path=output_path_for_url(config.output_dir, "/dup/"),
        layout="page.html",
        date=None,
        tags=[],
        draft=False,
        body_html="",
    )
    warnings: list[str] = []

    kept = dedupe_pages_by_url([first, second], warnings)

    assert kept == [first]
    assert any("skipping duplicate URL" in warning for warning in warnings)


def test_source_label_generated_page():
    page = Page(
        source_path=None,
        relative_source_path=None,
        title="Tag: python",
        slug="python",
        url="/tags/python/",
        output_path=Path("dist/tags/python/index.html"),
        layout="tag.html",
        date=None,
        tags=["python"],
        draft=False,
        body_html="",
        generated=True,
    )

    assert _source_label(page) == "generated page 'Tag: python'"


def test_render_nav_html_empty_root():
    root = NavNode(title="root")

    assert render_nav_html(root) == ""


def test_render_nav_branch_span_without_url():
    node = NavNode(title="Section", children={"leaf": NavNode(title="Leaf", url="/leaf/")})
    html = render_nav_html(node)

    assert "<span>Section</span>" in html
    assert "/leaf/" in html
