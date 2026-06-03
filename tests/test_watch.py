""" Test Watch """

from __future__ import annotations

from ssg.watch import DirectoryWatcher, ReloadState, watch_paths_for_config


def test_reload_state_bumps_version():
    state = ReloadState()
    assert state.current() == 0
    assert state.bump() == 1
    assert state.current() == 1


def test_watch_paths_include_site_config(site_root):
    paths = watch_paths_for_config(site_root / "site.toml")
    assert site_root / "site.toml" in paths
    assert site_root / "content" in paths


def test_directory_watcher_snapshot_changes(site_root):
    watcher = DirectoryWatcher([site_root / "content"])
    before = watcher._snapshot()
    (site_root / "content" / "watched.md").write_text("# Watched\n", encoding="utf-8")
    after = watcher._snapshot()
    assert before != after
