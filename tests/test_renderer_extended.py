""" Test Renderer Extended """

from __future__ import annotations

from pathlib import Path

import pytest

from ssg.config import load_config
from ssg.errors import TemplateRenderError
from ssg.models import Page
from ssg.renderer import (
    build_context,
    canonical_url,
    nav_to_context,
    page_to_context,
    prerender_partials,
    render_page,
    render_site,
)
from ssg.site_model import build_site_model
from ssg.template_adapter import TemplateRenderer
from tests.test_renderer import make_page


def test_canonical_url_without_base():
    assert canonical_url("", "/about/") == "/about/"


def test_canonical_url_with_base():
    assert canonical_url("https://example.com/", "/about/") == "https://example.com/about/"


def test_page_to_context_fields():
    page = Page(
        source_path=Path("content/x.md"),
        relative_source_path=Path("x.md"),
        title="T",
        slug="t",
        url="/t/",
        output_path=Path("dist/t/index.html"),
        layout="page.html",
        date="2026-01-01",
        tags=["a"],
        draft=False,
        body_html="",
        collection="blog",
        generated=False,
        previous_url="/prev/",
        next_url="/next/",
    )
    ctx = page_to_context(page)

    assert ctx["title"] == "T"
    assert ctx["previous_url"] == "/prev/"
    assert ctx["generated"] is False


def test_nav_to_context_nested():
    from ssg.models import NavNode

    root = NavNode(
        title="root",
        children={"about": NavNode(title="About", url="/about/")},
    )
    ctx = nav_to_context(root)

    assert ctx["title"] == "root"
    assert ctx["children"]["about"]["url"] == "/about/"


def test_render_site_reraises_without_error_collector(site_root):
    config = load_config(site_root / "site.toml")
    page = make_page(config, layout="missing.html")
    site = build_site_model(config, [page])

    from ssg.errors import MissingLayoutError

    with pytest.raises(MissingLayoutError):
        render_site(site)


def test_render_page_wraps_unexpected_exception(site_root):
    config = load_config(site_root / "site.toml")
    page = make_page(config)
    site = build_site_model(config, [page])

    class BrokenRenderer:
        def render(self, template_text, context):
            raise ValueError("boom")

    with pytest.raises(TemplateRenderError, match="boom"):
        render_page(page, site, BrokenRenderer(), {})


def test_build_context_includes_site_collections(site_root):
    config = load_config(site_root / "site.toml")
    site = build_site_model(config, [make_page(config)])
    page = site.pages[0]
    ctx = build_context(page, site, partials={})

    assert "collections" in ctx["site"]
    assert "tags" in ctx["site"]
    assert ctx["page"]["canonical_url"]


def test_prerender_partials_empty():
    assert prerender_partials(TemplateRenderer(), {}, {"page": {}, "site": {}}) == {}


def test_render_site_records_template_errors(site_root, monkeypatch):
    config = load_config(site_root / "site.toml")
    site = build_site_model(config, [make_page(config)])
    errors: list[str] = []
    failed: set[str] = set()

    def boom(*args, **kwargs):
        raise TemplateRenderError("render failed", path=site.pages[0].source_path)

    monkeypatch.setattr("ssg.renderer.render_page", boom)

    rendered = render_site(site, errors=errors, failed_page_keys=failed)

    assert rendered == []
    assert errors
    assert failed
