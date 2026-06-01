from __future__ import annotations

import pytest

from ssg.config import load_config
from ssg.errors import MissingLayoutError, TemplateRenderError
from ssg.models import Page
from ssg.page_builder import output_path_for_url
from ssg.renderer import build_context, load_partials, render_site
from ssg.site_model import build_site_model


def make_page(config, layout="page.html"):
    return Page(
        source_path=config.content_dir / "page.md",
        relative_source_path=None,
        title="Page",
        slug="page",
        url="/page/",
        output_path=output_path_for_url(config.output_dir, "/page/"),
        layout=layout,
        date=None,
        tags=[],
        draft=False,
        body_html="<h1>Page</h1>",
    )


def test_renderer_passes_page_body_and_partials(site_root):
    config = load_config(site_root / "site.toml")
    site = build_site_model(config, [make_page(config)])

    rendered = render_site(site)

    assert "<h1>Page</h1>" in rendered[0].html
    assert "<header>Header</header>" in rendered[0].html


def test_renderer_reports_missing_layout(site_root):
    config = load_config(site_root / "site.toml")
    site = build_site_model(config, [make_page(config, layout="missing.html")])

    with pytest.raises(MissingLayoutError):
        render_site(site)


def test_renderer_warns_when_partial_reference_is_missing(site_root):
    config = load_config(site_root / "site.toml")
    (config.layout_dir / "page.html").write_text(
        "<html>{{ site.partials.header }}{{ site.partials.missing }}</html>",
        encoding="utf-8",
    )
    site = build_site_model(config, [make_page(config)])

    render_site(site)

    assert any("missing" in warning for warning in site.warnings)


def test_partial_loader_returns_empty_when_dir_absent(tmp_path):
    assert load_partials(tmp_path / "nope") == {}


def test_partial_loader_skips_hidden(site_root):
    config = load_config(site_root / "site.toml")
    (config.partial_dir / ".hidden.html").write_text("nope", encoding="utf-8")
    (config.partial_dir / ".hidden-dir").mkdir()
    (config.partial_dir / ".hidden-dir" / "header.html").write_text("nope", encoding="utf-8")

    partials = load_partials(config.partial_dir)

    assert ".hidden" not in partials
    assert "header" in partials and "nope" not in partials["header"]


def test_partial_loader_rejects_duplicate_stem(site_root):
    config = load_config(site_root / "site.toml")
    (config.partial_dir / "blog").mkdir()
    (config.partial_dir / "blog" / "header.html").write_text("dup", encoding="utf-8")

    with pytest.raises(TemplateRenderError):
        load_partials(config.partial_dir)


def test_build_context_exposes_slug_collection_layout(site_root):
    config = load_config(site_root / "site.toml")
    page = make_page(config)
    page.collection = "blog"
    site = build_site_model(config, [page])

    context = build_context(page, site, partials={})

    assert context["page"]["slug"] == "page"
    assert context["page"]["collection"] == "blog"
    assert context["page"]["layout"] == "page.html"
    assert context["site"]["assets_dir"] == "assets"
    assert "collections" in context["site"]


def test_renderer_omits_empty_prev_next_links(site_root):
    config = load_config(site_root / "site.toml")
    (config.layout_dir / "post.html").write_text(
        (
            "<html>{% if page.previous_url %}"
            '<a href="{{ page.previous_url }}">Previous</a>'
            "{% endif %}"
            "{% if page.next_url %}"
            '<a href="{{ page.next_url }}">Next</a>'
            "{% endif %}</html>"
        ),
        encoding="utf-8",
    )
    page = make_page(config, layout="post.html")
    page.previous_url = None
    page.next_url = None
    site = build_site_model(config, [page])

    rendered = render_site(site)

    assert 'href=""' not in rendered[0].html
    assert "Previous" not in rendered[0].html
    assert "Next" not in rendered[0].html


def test_renderer_prerenders_partials_with_site_context(site_root):
    config = load_config(site_root / "site.toml")
    (config.partial_dir / "header.html").write_text("<h1>{{ site.title }}</h1>", encoding="utf-8")
    site = build_site_model(config, [make_page(config)])

    rendered = render_site(site)

    assert "<h1>Test Site</h1>" in rendered[0].html


def test_renderer_prerenders_nested_partials(site_root):
    config = load_config(site_root / "site.toml")
    (config.partial_dir / "wrap.html").write_text(
        "<div>{{ site.partials.inner | safe }}</div>", encoding="utf-8"
    )
    (config.partial_dir / "inner.html").write_text(
        "<span>{{ site.title }}</span>", encoding="utf-8"
    )
    (config.layout_dir / "page.html").write_text(
        "{{ site.partials.wrap | safe }}", encoding="utf-8"
    )
    site = build_site_model(config, [make_page(config)])

    rendered = render_site(site)

    assert "<div><span>Test Site</span></div>" in rendered[0].html


def test_renderer_exposes_nav_html(site_root):
    config = load_config(site_root / "site.toml")
    home = make_page(config)
    home.url = "/"
    home.title = "Home"
    site = build_site_model(config, [home])

    context = build_context(home, site, partials={})

    assert '<a href="/">Home</a>' in context["site"]["nav_html"]


def test_partial_warning_catches_filter_syntax(site_root):
    config = load_config(site_root / "site.toml")
    (config.layout_dir / "page.html").write_text(
        "<html>{{ site.partials.header }}{{ site.partials.missing | safe }}</html>",
        encoding="utf-8",
    )
    site = build_site_model(config, [make_page(config)])

    render_site(site)

    assert any("missing" in warning for warning in site.warnings)
