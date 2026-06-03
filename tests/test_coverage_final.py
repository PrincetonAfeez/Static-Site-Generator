""" Test Coverage Final """

from __future__ import annotations

import pytest

from ssg.config import load_config
from ssg.errors import ConfigError, TemplateRenderError
from ssg.page_builder import derive_title, warn_collection_slug_collisions
from ssg.renderer import load_partials, render_site
from ssg.site_model import _render_nav_branch
from ssg.models import NavNode


def test_config_rejects_missing_layout_dir(site_root):
    import shutil

    shutil.rmtree(site_root / "layouts")

    with pytest.raises(ConfigError, match="layout directory not found"):
        load_config(site_root / "site.toml")


def test_config_section_returns_empty_for_null():
    from pathlib import Path

    from ssg.config import _section

    assert _section({"scaffold": None}, "scaffold", Path("site.toml")) == {}


def test_derive_title_root_index():
    from pathlib import Path

    assert derive_title(Path("index.md"), {}) == "Home"


def test_warn_collection_skips_root_level_pages(site_root):
    from ssg.config import load_config
    from ssg.models import Page
    from ssg.page_builder import output_path_for_url

    config = load_config(site_root / "site.toml")
    page = Page(
        source_path=config.content_dir / "index.md",
        relative_source_path=__import__("pathlib").Path("index.md"),
        title="Home",
        slug="index",
        url="/",
        output_path=output_path_for_url(config.output_dir, "/"),
        layout="page.html",
        date=None,
        tags=[],
        draft=False,
        body_html="",
    )
    warnings: list[str] = []

    warn_collection_slug_collisions([page], warnings)

    assert warnings == []


def test_render_nav_branch_root_node():
    assert _render_nav_branch(NavNode(title="root")) == ""


def test_load_partials_reraises_duplicate(site_root):
    config = load_config(site_root / "site.toml")
    (config.partial_dir / "dup").mkdir()
    (config.partial_dir / "dup" / "header.html").write_text("a", encoding="utf-8")

    with pytest.raises(Exception, match="duplicate partial"):
        load_partials(config.partial_dir)


def test_warn_collection_skips_pages_without_relative_path(site_root):
    from ssg.models import Page
    from ssg.page_builder import output_path_for_url

    config = load_config(site_root / "site.toml")
    page = Page(
        source_path=config.content_dir / "x.md",
        relative_source_path=None,
        title="X",
        slug="x",
        url="/x/",
        output_path=output_path_for_url(config.output_dir, "/x/"),
        layout="page.html",
        date=None,
        tags=[],
        draft=False,
        body_html="",
    )
    warnings: list[str] = []

    warn_collection_slug_collisions([page], warnings)

    assert warnings == []


def test_generate_collection_pages_without_taken_urls(site_root):
    from ssg.site_model import generate_collection_pages

    config = load_config(site_root / "site.toml")
    from tests.test_site_model import make_page

    post = make_page(config, url="/blog/post/", title="Post", collection="blog")
    post.relative_source_path = __import__("pathlib").Path("blog/post.md")

    pages = generate_collection_pages(config, [post])

    assert any(page.generated and page.url == "/blog/" for page in pages)


def test_unescape_backslash_sequences():
    from ssg.frontmatter import _unescape_double_quoted, _unescape_single_quoted

    assert _unescape_single_quoted("\\\\") == "\\"
    assert _unescape_double_quoted("\\\\") == "\\"


def test_cli_print_build_summary_with_warnings(site_root, capsys):
    from ssg.builder import SiteBuilder
    from ssg.cli import print_build_summary

    import shutil

    shutil.rmtree(site_root / "static")
    result = SiteBuilder(site_root / "site.toml").build()
    print_build_summary(result)
    captured = capsys.readouterr()

    assert "warnings:" in captured.out
    assert "static directory not found" in captured.out


def test_cli_unknown_command_returns_two(monkeypatch):
    from ssg.cli import main

    class FakeParser:
        def parse_args(self, argv):
            class Args:
                command = "unknown"

            return Args()

    monkeypatch.setattr("ssg.cli.build_parser", lambda: FakeParser())

    assert main([]) == 2


def test_render_site_reraises_partial_load_error(site_root):
    from ssg.site_model import build_site_model
    from tests.test_renderer import make_page

    config = load_config(site_root / "site.toml")
    (config.partial_dir / "nested").mkdir()
    (config.partial_dir / "header.html").write_text("a", encoding="utf-8")
    (config.partial_dir / "nested" / "header.html").write_text("b", encoding="utf-8")
    site = build_site_model(config, [make_page(config)])

    with pytest.raises(TemplateRenderError, match="duplicate partial"):
        render_site(site)


def test_render_page_reraises_missing_layout_from_inner(site_root, monkeypatch):
    from ssg.errors import MissingLayoutError
    from ssg.renderer import render_page
    from ssg.site_model import build_site_model
    from tests.test_renderer import make_page

    config = load_config(site_root / "site.toml")
    page = make_page(config)
    site = build_site_model(config, [page])

    def raise_missing(*args, **kwargs):
        raise MissingLayoutError("inner missing", path=page.source_path)

    monkeypatch.setattr("ssg.renderer.prerender_partials", raise_missing)

    with pytest.raises(MissingLayoutError, match="inner missing"):
        render_page(
            page,
            site,
            __import__("ssg.template_adapter", fromlist=["TemplateRenderer"]).TemplateRenderer(),
            {},
        )


def test_render_page_generic_exception_becomes_template_error(site_root):
    from ssg.renderer import render_page
    from ssg.site_model import build_site_model
    from tests.test_renderer import make_page

    config = load_config(site_root / "site.toml")
    page = make_page(config)
    site = build_site_model(config, [page])

    class BrokenRenderer:
        def render(self, template_text, context):
            raise RuntimeError("unexpected render failure")

    with pytest.raises(TemplateRenderError, match="unexpected render failure"):
        render_page(page, site, BrokenRenderer(), {})
