""" Test Cache """

from __future__ import annotations

from ssg.builder import SiteBuilder
from ssg.cache import (
    compute_fingerprints,
    content_hashes,
    directory_tree_hash,
    file_content_hash,
    prune_stale_outputs,
    save_cache,
)
from ssg.config import load_config


def test_file_content_hash_is_stable(site_root):
    path = site_root / "content" / "index.md"
    first = file_content_hash(path)
    second = file_content_hash(path)
    assert first == second
    assert len(first) == 64


def test_prune_stale_outputs_removes_orphans(site_root):
    config = load_config(site_root / "site.toml")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    stale = config.output_dir / "old-page" / "index.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("<html></html>", encoding="utf-8")
    keep = config.output_dir / "index.html"
    keep.write_text("<html>home</html>", encoding="utf-8")

    removed = prune_stale_outputs(
        config,
        previous_files=["old-page/index.html", "index.html"],
        current_files={"index.html"},
    )

    assert removed == ["old-page/index.html"]
    assert not stale.exists()
    assert keep.exists()


def test_incremental_build_skips_clean_and_writes_cache(site_root):
    SiteBuilder(site_root / "site.toml").build()
    sentinel = site_root / "dist" / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")

    result = SiteBuilder(site_root / "site.toml", incremental=True).build()

    assert sentinel.exists()
    assert (site_root / "dist" / ".ssg-cache.json").exists()
    assert result.manifest.incremental is True


def test_incremental_build_prunes_deleted_page(site_root):
    SiteBuilder(site_root / "site.toml").build()
    about_output = site_root / "dist" / "about" / "index.html"
    assert about_output.exists()

    (site_root / "content" / "about.md").unlink()
    result = SiteBuilder(site_root / "site.toml", incremental=True).build()

    assert not about_output.exists()
    assert result.manifest.stale_files_removed >= 1


def test_save_cache_round_trip(site_root):
    config = load_config(site_root / "site.toml")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    fingerprints = compute_fingerprints(config, config_path=site_root / "site.toml")
    save_cache(config, fingerprints=fingerprints, output_files=["index.html"])
    assert (config.output_dir / ".ssg-cache.json").exists()


def test_directory_tree_hash_changes_when_file_changes(site_root):
    config = load_config(site_root / "site.toml")
    before = directory_tree_hash(config.static_dir)
    (config.static_dir / "new.txt").write_text("hello", encoding="utf-8")
    after = directory_tree_hash(config.static_dir)
    assert before != after


def test_content_hashes_include_markdown(site_root):
    config = load_config(site_root / "site.toml")
    hashes = content_hashes(config)
    assert any(path.endswith(".md") for path in hashes)
