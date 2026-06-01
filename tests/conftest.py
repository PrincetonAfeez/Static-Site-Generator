from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def site_root(tmp_path: Path) -> Path:
    root = tmp_path / "site"
    (root / "content" / "blog").mkdir(parents=True)
    (root / "layouts").mkdir()
    (root / "partials").mkdir()
    (root / "static" / "css").mkdir(parents=True)

    (root / "site.toml").write_text(
        "\n".join(
            [
                'title = "Test Site"',
                'base_url = "https://example.test"',
                'content_dir = "content"',
                'layout_dir = "layouts"',
                'partial_dir = "partials"',
                'static_dir = "static"',
                'output_dir = "dist"',
                'default_layout = "page.html"',
                'permalink = "/{path}/{slug}/"',
                "",
                "[build]",
                "drafts = false",
                "clean = true",
            ]
        ),
        encoding="utf-8",
    )
    (root / "layouts" / "page.html").write_text(
        (
            "<html><head><link rel=\"stylesheet\" href=\"/{{ site.assets_dir }}/css/style.css\">"
            "</head><body>{{ site.partials.header | safe }}"
            "<main>{{ page.body | safe }}</main></body></html>"
        ),
        encoding="utf-8",
    )
    (root / "layouts" / "post.html").write_text(
        "<html><body><article>{{ page.body | safe }}</article></body></html>",
        encoding="utf-8",
    )
    (root / "layouts" / "tag.html").write_text(
        "<html><body>{{ page.title }}{{ page.body | safe }}</body></html>",
        encoding="utf-8",
    )
    (root / "layouts" / "index.html").write_text(
        "<html><body>{{ page.body | safe }}</body></html>",
        encoding="utf-8",
    )
    (root / "partials" / "header.html").write_text("<header>Header</header>", encoding="utf-8")
    (root / "static" / "css" / "style.css").write_text("body { color: black; }", encoding="utf-8")
    (root / "content" / "index.md").write_text(
        "---\ntitle: Home\nlayout: page.html\ndraft: false\n---\n\n# Home\n",
        encoding="utf-8",
    )
    (root / "content" / "about.md").write_text(
        "---\ntitle: About\nlayout: page.html\ndraft: false\n---\n\n# About\n",
        encoding="utf-8",
    )
    (root / "content" / "blog" / "first.md").write_text(
        (
            "---\n"
            "title: First\n"
            "date: 2026-05-26\n"
            "tags: python, static-sites\n"
            "layout: post.html\n"
            "draft: false\n"
            "---\n\n"
            "# First\n"
        ),
        encoding="utf-8",
    )
    (root / "content" / "blog" / "draft.md").write_text(
        (
            "---\n"
            "title: Draft\n"
            "date: 2026-05-27\n"
            "tags: python\n"
            "layout: post.html\n"
            "draft: true\n"
            "---\n\n"
            "# Draft\n"
        ),
        encoding="utf-8",
    )
    return root
