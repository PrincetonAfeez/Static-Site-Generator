from __future__ import annotations

from ssg.config import load_config
from ssg.markdown_adapter import MarkdownConverter
from ssg.renderer import render_site
from ssg.site_model import build_site_model


def test_markdown_adapter_converts_heading():
    html = MarkdownConverter().convert("# Hello")

    assert "<h1>Hello</h1>" in html


def test_markdown_script_tags_require_safe_filter_in_layout(site_root):
    config = load_config(site_root / "site.toml")
    body_html = MarkdownConverter().convert('<script>alert("x")</script>\n\n# Title')
    from ssg.models import Page
    from ssg.page_builder import output_path_for_url

    page = Page(
        source_path=config.content_dir / "x.md",
        relative_source_path=None,
        title="X",
        slug="x",
        url="/x/",
        output_path=output_path_for_url(config.output_dir, "/x/"),
        layout="unsafe.html",
        date=None,
        tags=[],
        draft=False,
        body_html=body_html,
    )
    (config.layout_dir / "unsafe.html").write_text("<p>{{ page.body }}</p>", encoding="utf-8")
    site = build_site_model(config, [page])
    rendered = render_site(site)[0].html

    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_markdown_body_preserved_with_safe_filter(site_root):
    config = load_config(site_root / "site.toml")
    body_html = "<strong>bold</strong>"
    from ssg.models import Page
    from ssg.page_builder import output_path_for_url

    page = Page(
        source_path=config.content_dir / "safe.md",
        relative_source_path=None,
        title="Safe",
        slug="safe",
        url="/safe/",
        output_path=output_path_for_url(config.output_dir, "/safe/"),
        layout="safe.html",
        date=None,
        tags=[],
        draft=False,
        body_html=body_html,
    )
    (config.layout_dir / "safe.html").write_text(
        "<div>{{ page.body | safe }}</div>", encoding="utf-8"
    )
    site = build_site_model(config, [page])
    rendered = render_site(site)[0].html

    assert rendered == "<div><strong>bold</strong></div>"
