""" Test Pipeline Integration """

from __future__ import annotations

import shutil
from pathlib import Path

from ssg.builder import SiteBuilder


def test_pipeline_builds_example_site(site_root):
    result = SiteBuilder(site_root / "site.toml").build()

    assert result.manifest.pages_discovered == 4
    assert result.manifest.drafts_skipped == 1
    assert result.manifest.generated_pages == 3
    assert result.manifest.warnings == []
    assert result.manifest.errors == []
    assert result.manifest.pages_failed == 0
    assert (site_root / "dist" / "index.html").exists()
    assert (site_root / "dist" / "about" / "index.html").exists()
    assert (site_root / "dist" / "blog" / "first" / "index.html").exists()
    assert (site_root / "dist" / "blog" / "draft" / "index.html").exists() is False
    assert (site_root / "dist" / "tags" / "python" / "index.html").exists()
    assert (site_root / "dist" / "assets" / "css" / "style.css").exists()
    assert (site_root / "dist" / ".ssg-manifest.json").exists()
    assert ".ssg-manifest.json" in result.manifest.output_files
    assert result.manifest.schema_version == 1


def test_pipeline_includes_drafts_when_requested(site_root):
    SiteBuilder(site_root / "site.toml", include_drafts=True).build()

    assert (site_root / "dist" / "blog" / "draft" / "index.html").exists()


def test_pipeline_drafts_appear_in_tag_pages_when_included(site_root):
    SiteBuilder(site_root / "site.toml", include_drafts=True).build()

    python_tag = (site_root / "dist" / "tags" / "python" / "index.html").read_text(encoding="utf-8")
    assert "/blog/draft/" in python_tag
    assert "/blog/first/" in python_tag


def test_pipeline_manifest_uses_posix_paths(site_root):
    result = SiteBuilder(site_root / "site.toml").build()

    for name in result.manifest.output_files:
        assert "\\" not in name, f"manifest path uses backslash: {name}"


def test_pipeline_reports_failed_pages(site_root):
    bad = site_root / "content" / "broken.md"
    bad.write_text("---\ntitle: Broken\ndraft: maybe\n---\n", encoding="utf-8")

    result = SiteBuilder(site_root / "site.toml", continue_on_error=True).build()

    assert result.manifest.pages_failed == 0
    assert len(result.manifest.errors) >= 1
    assert any("broken.md" in error for error in result.manifest.errors)


def test_pipeline_honors_custom_assets_dir(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "[build]", 'assets_dir = "files"\n\n[build]'
        ),
        encoding="utf-8",
    )

    SiteBuilder(config_path).build()

    assert (site_root / "dist" / "files" / "css" / "style.css").exists()
    assert not (site_root / "dist" / "assets").exists()

    index_html = (site_root / "dist" / "index.html").read_text(encoding="utf-8")
    assert 'href="/files/css/style.css"' in index_html


def test_pipeline_builds_real_example_site(tmp_path):
    project_root = Path(__file__).resolve().parent.parent
    src = project_root / "example_site"
    dst = tmp_path / "example_site"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("dist"))

    result = SiteBuilder(dst / "site.toml").build()

    assert (dst / "dist" / "index.html").exists()
    assert (dst / "dist" / "about" / "index.html").exists()
    assert (dst / "dist" / "blog" / "first-post" / "index.html").exists()
    assert (dst / "dist" / "blog" / "index.html").exists()
    assert (dst / "dist" / "tags" / "python" / "index.html").exists()
    assert (dst / "dist" / "tags" / "static-sites" / "index.html").exists()
    assert (dst / "dist" / "assets" / "css" / "style.css").exists()
    assert (dst / "dist" / ".ssg-manifest.json").exists()

    rendered_html = (dst / "dist" / "index.html").read_text(encoding="utf-8")
    assert "Example Static Site" in rendered_html
    assert 'href="/assets/css/style.css"' in rendered_html
    assert 'rel="canonical" href="https://example.com/' in rendered_html
    assert 'href=""' not in (dst / "dist" / "blog" / "first-post" / "index.html").read_text(
        encoding="utf-8"
    )

    assert result.manifest.pages_rendered >= 6
    assert result.manifest.warnings == []
    assert result.manifest.errors == []


def test_pipeline_continue_on_error_survives_missing_layout(site_root):
    bad = site_root / "content" / "missing-layout.md"
    bad.write_text(
        "---\ntitle: NoLayout\nlayout: nope.html\ndraft: false\n---\n# x\n",
        encoding="utf-8",
    )

    result = SiteBuilder(site_root / "site.toml", continue_on_error=True).build()

    assert result.manifest.pages_failed >= 1
    assert any("nope.html" in error for error in result.manifest.errors)
    assert (site_root / "dist" / "index.html").exists()


def test_pipeline_warns_when_static_dir_missing(site_root):
    import shutil

    shutil.rmtree(site_root / "static")
    result = SiteBuilder(site_root / "site.toml").build()

    assert any("static directory not found" in warning for warning in result.manifest.warnings)


def test_pipeline_continue_on_error_survives_duplicate_url(site_root):
    (site_root / "content" / "collision.md").write_text(
        "---\ntitle: Collision\nslug: about\nlayout: page.html\ndraft: false\n---\n# x\n",
        encoding="utf-8",
    )

    result = SiteBuilder(site_root / "site.toml", continue_on_error=True).build()

    assert result.manifest.pages_failed >= 1
    assert any("duplicate URL" in error for error in result.manifest.errors)
    assert (site_root / "dist" / "index.html").exists()
    assert result.manifest.generated_pages >= 3
    assert (site_root / "dist" / "tags" / "python" / "index.html").exists()


def test_pipeline_warns_when_partial_dir_missing(site_root):
    import shutil

    shutil.rmtree(site_root / "partials")
    result = SiteBuilder(site_root / "site.toml").build()

    assert any("partial directory not found" in warning for warning in result.manifest.warnings)


def test_pipeline_continue_on_error_survives_asset_copy_failure(site_root, monkeypatch):
    from ssg.errors import AssetCopyError

    def fail_copy(_config, **kwargs):
        raise AssetCopyError("disk full", path=site_root / "static")

    monkeypatch.setattr("ssg.builder.copy_assets", fail_copy)

    result = SiteBuilder(site_root / "site.toml", continue_on_error=True).build()

    assert result.manifest.pages_failed == 0
    assert any("disk full" in error for error in result.manifest.errors)
    assert (site_root / "dist" / "index.html").exists()


def test_pipeline_manifest_omits_self_when_write_fails(site_root, monkeypatch):
    import ssg.builder as builder_module

    original = builder_module.write_manifest
    calls = {"count": 0}

    def flaky_write(config, manifest):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("manifest write failed")
        return original(config, manifest)

    monkeypatch.setattr(builder_module, "write_manifest", flaky_write)

    result = SiteBuilder(site_root / "site.toml", continue_on_error=True).build()

    assert any("manifest write failed" in error for error in result.manifest.errors)
    assert ".ssg-manifest.json" not in result.manifest.output_files
