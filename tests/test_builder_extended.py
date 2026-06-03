""" Test Builder Extended """

from __future__ import annotations

import pytest

from ssg.builder import SiteBuilder
from ssg.errors import AssetCopyError, MissingLayoutError, SiteModelError
from ssg.site_model import build_site_model


def test_builder_raises_site_model_error_without_continue(site_root):
    (site_root / "content" / "collision.md").write_text(
        "---\ntitle: Collision\nslug: about\nlayout: page.html\ndraft: false\n---\n# x\n",
        encoding="utf-8",
    )

    with pytest.raises(SiteModelError):
        SiteBuilder(site_root / "site.toml", continue_on_error=False).build()


def test_builder_raises_missing_layout_without_continue(site_root):
    (site_root / "content" / "bad-layout.md").write_text(
        "---\ntitle: Bad\nlayout: missing.html\ndraft: false\n---\n# x\n",
        encoding="utf-8",
    )

    with pytest.raises(MissingLayoutError):
        SiteBuilder(site_root / "site.toml", continue_on_error=False).build()


def test_builder_raises_asset_copy_error_without_continue(site_root, monkeypatch):
    def fail_copy(_config, **kwargs):
        raise AssetCopyError("disk full", path=site_root / "static")

    monkeypatch.setattr("ssg.builder.copy_assets", fail_copy)

    with pytest.raises(AssetCopyError):
        SiteBuilder(site_root / "site.toml", continue_on_error=False).build()


def test_builder_site_model_double_fallback(monkeypatch, site_root):
    calls = {"count": 0}
    original = build_site_model

    def flaky_build(config, pages, warnings=None):
        calls["count"] += 1
        if calls["count"] <= 2:
            raise SiteModelError(
                "duplicate URL /x/",
                conflicting_urls=frozenset({"/x/"}),
            )
        return original(config, pages, warnings=warnings)

    monkeypatch.setattr("ssg.builder.build_site_model", flaky_build)

    result = SiteBuilder(site_root / "site.toml", continue_on_error=True).build()

    assert calls["count"] == 3
    assert result.manifest.pages_rendered >= 1


def test_builder_manifest_second_write_failure(site_root, monkeypatch):
    import ssg.builder as builder_module

    original = builder_module.write_manifest
    calls = {"count": 0}

    def flaky_write(config, manifest):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("second write failed")
        return original(config, manifest)

    monkeypatch.setattr(builder_module, "write_manifest", flaky_write)

    result = SiteBuilder(site_root / "site.toml", continue_on_error=True).build()

    assert any("second write failed" in error for error in result.manifest.errors)


def test_builder_manifest_write_fatal_without_continue(site_root, monkeypatch):
    import ssg.builder as builder_module

    def fail_write(_config, _manifest):
        raise OSError("manifest write failed")

    monkeypatch.setattr(builder_module, "write_manifest", fail_write)

    from ssg.errors import OutputWriteError

    with pytest.raises(OutputWriteError):
        SiteBuilder(site_root / "site.toml", continue_on_error=False).build()


def test_builder_manifest_second_write_fatal_without_continue(site_root, monkeypatch):
    import ssg.builder as builder_module

    original = builder_module.write_manifest
    calls = {"count": 0}

    def flaky_write(config, manifest):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("second write failed")
        return original(config, manifest)

    monkeypatch.setattr(builder_module, "write_manifest", flaky_write)

    from ssg.errors import OutputWriteError

    with pytest.raises(OutputWriteError):
        SiteBuilder(site_root / "site.toml", continue_on_error=False).build()


def test_builder_clean_output_false_creates_output_dir(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("clean = true", "clean = false"),
        encoding="utf-8",
    )
    dist = site_root / "dist"
    if dist.exists():
        import shutil

        shutil.rmtree(dist)

    SiteBuilder(config_path, clean_output=False).build()

    assert dist.exists()
