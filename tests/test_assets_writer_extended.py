""" Test Assets Writer Extended """

from __future__ import annotations

import pytest

from ssg.assets import copy_assets
from ssg.config import load_config
from ssg.errors import AssetCopyError
from ssg.models import Page, RenderedPage
from ssg.page_builder import output_path_for_url
from ssg.writer import clean_output_dir, remove_output_dir, write_pages


def test_assets_rejects_static_file_not_directory(site_root):
    config = load_config(site_root / "site.toml")
    static_file = site_root / "static"
    import shutil

    shutil.rmtree(static_file)
    static_file.write_text("not a dir", encoding="utf-8")

    with pytest.raises(AssetCopyError, match="not a directory"):
        copy_assets(config)


def test_assets_skips_hidden_and_directories(site_root):
    config = load_config(site_root / "site.toml")
    clean_output_dir(config)
    (config.static_dir / ".hidden.css").write_text("hidden", encoding="utf-8")
    (config.static_dir / "nested").mkdir()
    (config.static_dir / "nested" / "ignored.tmp").write_text("x", encoding="utf-8")

    copied = copy_assets(config)

    assert all(".hidden" not in str(path) for path in copied)
    assert (config.output_dir / "assets" / "nested" / "ignored.tmp") in copied


def test_assets_copy_oserror(site_root, monkeypatch):
    import ssg.assets as assets_module

    config = load_config(site_root / "site.toml")
    clean_output_dir(config)

    def fail_copy2(*args, **kwargs):
        raise OSError("copy failed")

    monkeypatch.setattr(assets_module.shutil, "copy2", fail_copy2)

    with pytest.raises(AssetCopyError, match="copy failed"):
        copy_assets(config)


def test_write_pages_continue_on_error(site_root):

    config = load_config(site_root / "site.toml")
    clean_output_dir(config)
    good = Page(
        source_path=config.content_dir / "good.md",
        relative_source_path=None,
        title="Good",
        slug="good",
        url="/good/",
        output_path=output_path_for_url(config.output_dir, "/good/"),
        layout="page.html",
        date=None,
        tags=[],
        draft=False,
        body_html="",
    )
    bad = Page(
        source_path=config.content_dir / "bad.md",
        relative_source_path=None,
        title="Bad",
        slug="bad",
        url="/bad/",
        output_path=config.output_dir.parent / "outside" / "index.html",
        layout="page.html",
        date=None,
        tags=[],
        draft=False,
        body_html="",
    )
    errors: list[str] = []
    failed: set[str] = set()

    written = write_pages(
        config,
        [
            RenderedPage(page=good, html="<p>ok</p>"),
            RenderedPage(page=bad, html="<p>nope</p>"),
        ],
        errors=errors,
        failed_page_keys=failed,
    )

    assert written == [good.output_path]
    assert len(errors) == 1
    assert "/bad/" in failed


def test_write_pages_oserror(site_root, monkeypatch):
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
    rendered = RenderedPage(page=page, html="x")

    def fail_write(self, *args, **kwargs):
        raise OSError("write failed")

    monkeypatch.setattr(type(rendered.page.output_path), "write_text", fail_write)

    from ssg.errors import OutputWriteError

    with pytest.raises(OutputWriteError):
        write_pages(config, [rendered])


def test_remove_output_dir(site_root):
    config = load_config(site_root / "site.toml")
    clean_output_dir(config)
    assert config.output_dir.exists()

    remove_output_dir(config)

    assert not config.output_dir.exists()
