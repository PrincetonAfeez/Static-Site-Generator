""" Test New Features """

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest

from ssg.assets import copy_assets, read_manifest_output_files
from ssg.builder import SiteBuilder
from ssg.cache import (
    fingerprints_from_cache,
    load_cache,
    prune_stale_outputs,
)
from ssg.cli import LIVE_RELOAD_SNIPPET, main
from ssg.config import load_config
from ssg.errors import OutputWriteError
from ssg.frontmatter import normalize_value, parse_yaml_metadata
from ssg.models import SourceFile
from ssg.sitemap import render_sitemap
from ssg.site_model import build_site_model
from ssg.watch import ReloadState, run_watch
from tests.test_renderer import make_page


def test_read_manifest_output_files_returns_empty_for_bad_json(site_root):
    config = load_config(site_root / "site.toml")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    (config.output_dir / ".ssg-manifest.json").write_text("{bad", encoding="utf-8")

    assert read_manifest_output_files(config) == []


def test_copy_assets_skips_when_static_unchanged(site_root):
    config = load_config(site_root / "site.toml")
    SiteBuilder(site_root / "site.toml").build()
    first = copy_assets(config)
    second = copy_assets(
        config,
        skip_if_unchanged=True,
        previous_static_hash="same",
        current_static_hash="same",
    )

    assert first
    assert second


def test_load_cache_rejects_invalid_schema(site_root):
    config = load_config(site_root / "site.toml")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    (config.output_dir / ".ssg-cache.json").write_text('{"schema_version": 99}', encoding="utf-8")

    assert load_cache(config) is None


def test_fingerprints_from_cache_rejects_bad_payload():
    assert fingerprints_from_cache({"content_hashes": "nope"}) is None


def test_prune_skips_protected_files(site_root):
    config = load_config(site_root / "site.toml")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = config.output_dir / ".ssg-manifest.json"
    manifest.write_text("{}", encoding="utf-8")

    removed = prune_stale_outputs(
        config,
        previous_files=[".ssg-manifest.json"],
        current_files=set(),
    )

    assert removed == []
    assert manifest.exists()


def test_cli_build_incremental_flag(site_root, capsys):
    assert main(["build", "--config", str(site_root / "site.toml"), "--incremental"]) == 0
    captured = capsys.readouterr()
    assert "incremental: yes" in captured.out


def test_cli_watch_no_serve_rebuilds_once(site_root, monkeypatch):
    calls = {"count": 0}

    class ImmediateWatcher:
        def __init__(self, paths):
            self.paths = paths
            self._snapshots = {}

        def _snapshot(self):
            return {}

        def wait_for_change(self):
            calls["count"] += 1
            if calls["count"] > 1:
                raise KeyboardInterrupt

    monkeypatch.setattr("ssg.watch.DirectoryWatcher", ImmediateWatcher)

    assert main(["watch", "--config", str(site_root / "site.toml"), "--no-serve"]) == 0


def test_serve_live_reload_injects_script(site_root):
    import ssg.cli as cli_module
    from ssg.builder import SiteBuilder

    SiteBuilder(site_root / "site.toml").build()
    config = load_config(site_root / "site.toml")
    html_path = config.output_dir / "index.html"
    html_path.write_text("<html><body>Home</body></html>", encoding="utf-8")

    handler = cli_module._build_handler(config.output_dir, ReloadState())

    class TestHandler(handler):
        directory = str(config.output_dir)

        def __init__(self):
            self.path = "/index.html"
            self.command = "GET"
            self.wfile = BytesIO()

        def send_response(self, code):
            self.status = code

        def send_header(self, key, value):
            pass

        def end_headers(self):
            pass

    test_handler = TestHandler()
    test_handler.send_head()
    body = test_handler.wfile.getvalue().decode("utf-8")
    assert LIVE_RELOAD_SNIPPET.strip() in body


def test_serve_reload_endpoint(site_root):
    from ssg.builder import SiteBuilder

    SiteBuilder(site_root / "site.toml").build()
    state = ReloadState()
    state.bump()
    handler_cls = __import__("ssg.cli", fromlist=["_build_handler"])._build_handler(
        site_root / "dist",
        state,
    )

    class Handler(handler_cls):
        def __init__(self):
            self.path = "/__ssg_reload"
            self.wfile = BytesIO()
            self.headers = {}

        def send_response(self, code):
            self.status = code

        def send_header(self, key, value):
            pass

        def end_headers(self):
            pass

    handler = Handler()
    handler.do_GET()
    assert handler.wfile.getvalue() == b"1"


def test_builder_continue_on_error_records_sitemap_failure(site_root, monkeypatch):
    def fail_write(config, site):
        raise OSError("disk full")

    monkeypatch.setattr("ssg.builder.write_sitemap", fail_write)

    result = SiteBuilder(site_root / "site.toml", continue_on_error=True).build()

    assert any("sitemap.xml" in error for error in result.manifest.errors)


def test_render_sitemap_skips_pages_without_base_url(site_root):
    config = load_config(site_root / "site.toml")
    config = __import__("dataclasses").replace(config, base_url="")
    page = make_page(config)
    site = build_site_model(config, [page])

    xml = render_sitemap(config, site)

    assert "<loc>" not in xml


def test_parse_yaml_metadata_rejects_non_string_keys(site_root):
    source = SourceFile(path=Path("x.md"), relative_path=Path("x.md"), extension=".md")

    with pytest.raises(Exception, match="strings"):
        parse_yaml_metadata("{1: two}", source, [])


def test_normalize_value_coerces_numbers(site_root):
    source = SourceFile(path=Path("x.md"), relative_path=Path("x.md"), extension=".md")

    assert normalize_value("author", 42, source, 1) == "42"


def test_global_deps_changed_without_previous(site_root):
    from ssg.cache import compute_fingerprints

    config = load_config(site_root / "site.toml")
    fingerprints = compute_fingerprints(config, config_path=site_root / "site.toml")
    assert fingerprints.global_deps_changed(None) is True


def test_directory_tree_hash_skips_hidden_files(site_root):
    from ssg.cache import directory_tree_hash

    config = load_config(site_root / "site.toml")
    (config.static_dir / ".secret").write_text("x", encoding="utf-8")
    digest = directory_tree_hash(config.static_dir)
    (config.static_dir / "visible.txt").write_text("y", encoding="utf-8")
    assert digest != directory_tree_hash(config.static_dir)


def test_content_hashes_skips_hidden_and_non_markdown(site_root):
    from ssg.cache import content_hashes

    config = load_config(site_root / "site.toml")
    (config.content_dir / ".hidden.md").write_text("---\ntitle: x\n---\n", encoding="utf-8")
    (config.content_dir / "note.txt").write_text("plain", encoding="utf-8")
    hashes = content_hashes(config)
    assert not any(".hidden" in key for key in hashes)
    assert not any(key.endswith(".txt") for key in hashes)


def test_load_cache_returns_none_for_non_dict(site_root):
    config = load_config(site_root / "site.toml")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    (config.output_dir / ".ssg-cache.json").write_text("[]", encoding="utf-8")
    assert load_cache(config) is None


def test_fingerprints_from_cache_missing_keys():
    assert fingerprints_from_cache({}) is None


def test_prune_removes_empty_parent_directories(site_root):
    config = load_config(site_root / "site.toml")
    nested = config.output_dir / "old" / "nested" / "index.html"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("x", encoding="utf-8")

    removed = prune_stale_outputs(
        config,
        previous_files=["old/nested/index.html"],
        current_files=set(),
    )

    assert removed == ["old/nested/index.html"]
    assert not (config.output_dir / "old").exists()


def test_directory_watcher_wait_for_change(site_root):
    from ssg.watch import DirectoryWatcher

    watcher = DirectoryWatcher([site_root / "content"], poll_interval=0.01)
    (site_root / "content" / "trigger.md").write_text("# trigger\n", encoding="utf-8")
    watcher.wait_for_change()


def test_serve_background_records_errors(site_root, monkeypatch):
    from ssg.watch import _serve_background

    def fail_serve(*args, **kwargs):
        raise RuntimeError("serve failed")

    monkeypatch.setattr("ssg.cli.serve", fail_serve)
    errors: list[BaseException] = []
    _serve_background(site_root / "site.toml", "127.0.0.1", 8000, None, errors)
    assert len(errors) == 1


def test_run_watch_build_error(site_root, monkeypatch):
    class BrokenBuilder:
        def __init__(self, *args, **kwargs):
            pass

        def build(self):
            from ssg.errors import ConfigError

            raise ConfigError("broken")

    monkeypatch.setattr("ssg.watch.SiteBuilder", BrokenBuilder)

    class ImmediateWatcher:
        def __init__(self, paths):
            self._snapshots = {}

        def _snapshot(self):
            return {}

        def wait_for_change(self):
            raise KeyboardInterrupt

    monkeypatch.setattr("ssg.watch.DirectoryWatcher", ImmediateWatcher)
    assert run_watch(site_root / "site.toml", serve_site=False, quiet=True) == 1


def test_incremental_warns_when_layout_changes(site_root):
    SiteBuilder(site_root / "site.toml").build()
    (site_root / "layouts" / "page.html").write_text(
        (site_root / "layouts" / "page.html").read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    result = SiteBuilder(site_root / "site.toml", incremental=True).build()
    assert any("global dependencies changed" in warning for warning in result.manifest.warnings)


def test_builder_raises_when_sitemap_write_fails(site_root, monkeypatch):
    def fail_write(config, site):
        raise OSError("disk full")

    monkeypatch.setattr("ssg.builder.write_sitemap", fail_write)

    with pytest.raises(OutputWriteError):
        SiteBuilder(site_root / "site.toml", continue_on_error=False).build()


def test_serve_html_without_body_tag_gets_reload_snippet(site_root):
    import ssg.cli as cli_module
    from ssg.builder import SiteBuilder

    SiteBuilder(site_root / "site.toml").build()
    config = load_config(site_root / "site.toml")
    html_path = config.output_dir / "plain.html"
    html_path.write_text("<html>Plain</html>", encoding="utf-8")

    handler = cli_module._build_handler(config.output_dir, ReloadState())

    class TestHandler(handler):
        directory = str(config.output_dir)

        def __init__(self):
            self.path = "/plain.html"
            self.command = "GET"
            self.wfile = BytesIO()

        def send_response(self, code):
            pass

        def send_header(self, key, value):
            pass

        def end_headers(self):
            pass

    test_handler = TestHandler()
    test_handler.send_head()
    assert LIVE_RELOAD_SNIPPET.strip() in test_handler.wfile.getvalue().decode("utf-8")


def test_read_manifest_output_files_rejects_non_list(site_root):
    config = load_config(site_root / "site.toml")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    (config.output_dir / ".ssg-manifest.json").write_text(
        json.dumps({"output_files": "not-a-list"}),
        encoding="utf-8",
    )
    assert read_manifest_output_files(config) == []


def test_list_existing_assets_when_assets_missing(site_root):
    from ssg.assets import _list_existing_assets

    config = load_config(site_root / "site.toml")
    assert _list_existing_assets(config) == []


def test_run_watch_starts_background_server(site_root, monkeypatch):
    class ImmediateWatcher:
        def __init__(self, paths):
            self._snapshots = {}

        def _snapshot(self):
            return {}

        def wait_for_change(self):
            raise KeyboardInterrupt

    class FakeThread:
        def __init__(self, target, args, daemon):
            self._target = target
            self._args = args

        def start(self):
            self._target(*self._args)

    monkeypatch.setattr("ssg.watch.DirectoryWatcher", ImmediateWatcher)
    monkeypatch.setattr("ssg.watch.threading.Thread", FakeThread)
    monkeypatch.setattr("ssg.cli.serve", lambda *args, **kwargs: None)
    SiteBuilder(site_root / "site.toml").build()
    assert run_watch(site_root / "site.toml", serve_site=True, quiet=True) == 0


def test_frontmatter_rejects_invalid_tag_items(site_root):
    source = SourceFile(path=Path("x.md"), relative_path=Path("x.md"), extension=".md")

    with pytest.raises(Exception, match="strings"):
        parse_yaml_metadata("tags:\n  - 1\n", source, [])


def test_sitemap_deduplicates_urls(site_root):
    from ssg.sitemap import _sitemap_urls

    config = load_config(site_root / "site.toml")
    page = make_page(config)
    duplicate = make_page(config)
    urls = _sitemap_urls(config, [page, duplicate])
    assert len(urls) == 1


def test_frontmatter_yaml_list_and_multiline(site_root):
    source = SourceFile(path=Path("x.md"), relative_path=Path("x.md"), extension=".md")
    metadata = parse_yaml_metadata(
        "description: |\n  Line one\n  Line two\ntags:\n  - Alpha\n  - Beta",
        source,
        [],
    )
    assert "Line one" in metadata["description"]
    assert metadata["tags"] == ["alpha", "beta"]
