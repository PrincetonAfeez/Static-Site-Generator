""" Test Page Builder """

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from ssg.config import load_config
from ssg.errors import PageBuildError
from ssg.frontmatter import parse_document
from ssg.markdown_adapter import MarkdownConverter
from ssg.models import SourceFile
from ssg.page_builder import build_page, derive_url


def build_page_from_path(path, root):
    config = load_config(root / "site.toml")
    source = SourceFile(
        path=path, relative_path=path.relative_to(root / "content"), extension=path.suffix
    )
    document = parse_document(source)
    html = MarkdownConverter().convert(document.body_markdown)
    return build_page(document, html, config)


def test_page_builder_derives_url_and_output_path(site_root):
    page = build_page_from_path(site_root / "content" / "blog" / "first.md", site_root)

    assert page.slug == "first"
    assert page.url == "/blog/first/"
    assert page.output_path == site_root / "dist" / "blog" / "first" / "index.html"
    assert page.collection == "blog"


def test_page_builder_maps_root_index_to_slash(site_root):
    page = build_page_from_path(site_root / "content" / "index.md", site_root)

    assert page.url == "/"
    assert page.output_path == site_root / "dist" / "index.html"


def test_derive_url_honors_custom_permalink():
    from pathlib import Path

    url = derive_url(Path("blog/post.md"), "post", permalink="/articles/{slug}/")
    assert url == "/articles/post/"

    url = derive_url(Path("blog/post.md"), "post", permalink="/{path}/{slug}/")
    assert url == "/blog/post/"


def test_page_builder_rejects_slug_with_traversal(site_root):
    path = site_root / "content" / "evil.md"
    path.write_text(
        "---\ntitle: Evil\nslug: ../../etc\nlayout: page.html\ndraft: false\n---\n# Evil\n",
        encoding="utf-8",
    )
    config = load_config(site_root / "site.toml")
    source = SourceFile(
        path=path, relative_path=path.relative_to(site_root / "content"), extension=path.suffix
    )
    document = parse_document(source)
    html = MarkdownConverter().convert(document.body_markdown)

    with pytest.raises(PageBuildError):
        build_page(document, html, config)


def test_custom_permalink_applied_through_build_page(site_root):
    config = load_config(site_root / "site.toml")
    config = dataclasses.replace(config, permalink="/posts/{path}/{slug}.html/")
    path = site_root / "content" / "blog" / "first.md"
    source = SourceFile(
        path=path, relative_path=path.relative_to(site_root / "content"), extension=path.suffix
    )
    document = parse_document(source)
    html = MarkdownConverter().convert(document.body_markdown)

    page = build_page(document, html, config)

    assert page.url == "/posts/blog/first.html/"


def test_warn_collection_slug_collisions(site_root):
    from ssg.page_builder import build_page, warn_collection_slug_collisions
    from ssg.frontmatter import parse_document
    from ssg.markdown_adapter import MarkdownConverter
    from ssg.models import SourceFile

    config = load_config(site_root / "site.toml")
    warnings: list[str] = []
    pages = []
    for name in ("foo bar", "foo-bar"):
        path = site_root / "content" / name / "post.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\ntitle: Post\n---\n# Post\n", encoding="utf-8")
        source = SourceFile(
            path=path,
            relative_path=path.relative_to(site_root / "content"),
            extension=".md",
        )
        document = parse_document(source)
        pages.append(
            build_page(document, MarkdownConverter().convert(document.body_markdown), config)
        )

    warn_collection_slug_collisions(pages, warnings)

    assert any("foo bar" in warning and "foo-bar" in warning for warning in warnings)


@pytest.mark.parametrize(
    ("relative", "slug", "permalink", "expected"),
    [
        (Path("index.md"), "index", "/{path}/{slug}/", "/"),
        (Path("about.md"), "about", "/{path}/{slug}/", "/about/"),
        (Path("blog/post.md"), "post", "/{slug}/", "/post/"),
        (Path("docs/guide.md"), "guide", "/{path}/{slug}/", "/docs/guide/"),
    ],
)
def test_derive_url_table(relative, slug, permalink, expected):
    assert derive_url(relative, slug, permalink=permalink) == expected
