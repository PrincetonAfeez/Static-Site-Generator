""" Test Writer Assets """

from __future__ import annotations

import pytest

from ssg.assets import copy_assets
from ssg.config import load_config
from ssg.errors import OutputWriteError
from ssg.models import Page, RenderedPage
from ssg.page_builder import output_path_for_url
from ssg.writer import clean_output_dir, ensure_inside_output, write_pages


def test_writer_writes_html(site_root):
    config = load_config(site_root / "site.toml")
    clean_output_dir(config)
    page = Page(
        source_path=config.content_dir / "page.md",
        relative_source_path=None,
        title="Page",
        slug="page",
        url="/page/",
        output_path=output_path_for_url(config.output_dir, "/page/"),
        layout="page.html",
        date=None,
        tags=[],
        draft=False,
        body_html="",
    )

    written = write_pages(config, [RenderedPage(page=page, html="<h1>Page</h1>")])

    assert written == [config.output_dir / "page" / "index.html"]
    assert written[0].read_text(encoding="utf-8") == "<h1>Page</h1>"


def test_assets_copy_to_dist_assets(site_root):
    config = load_config(site_root / "site.toml")
    clean_output_dir(config)

    copied = copy_assets(config)

    assert copied == [config.output_dir / "assets" / "css" / "style.css"]
    assert copied[0].exists()


def test_ensure_inside_output_rejects_escape(site_root):
    config = load_config(site_root / "site.toml")
    escapee = site_root / "outside.html"

    with pytest.raises(OutputWriteError):
        ensure_inside_output(config, escapee)


def test_assets_returns_empty_when_static_dir_absent(site_root):
    import shutil

    shutil.rmtree(site_root / "static")
    config = load_config(site_root / "site.toml")
    clean_output_dir(config)

    assert copy_assets(config) == []
