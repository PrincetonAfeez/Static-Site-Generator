""" Static Site Generator Watch """

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from .builder import SiteBuilder
from .config import load_config
from .errors import SSGError

logger = logging.getLogger("ssg.watch")


class ReloadState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.version = 0

    def bump(self) -> int:
        with self._lock:
            self.version += 1
            return self.version

    def current(self) -> int:
        with self._lock:
            return self.version


class DirectoryWatcher:
    def __init__(self, paths: list[Path], *, poll_interval: float = 0.25) -> None:
        self.paths = paths
        self.poll_interval = poll_interval
        self._snapshots = self._snapshot()

    def _snapshot(self) -> dict[Path, float]:
        state: dict[Path, float] = {}
        for root in self.paths:
            if not root.exists():
                state[root] = 0.0
                continue
            if root.is_file():
                state[root] = root.stat().st_mtime
                continue
            for path in root.rglob("*"):
                if path.is_file() and not any(
                    part.startswith(".") for part in path.relative_to(root).parts
                ):
                    state[path] = path.stat().st_mtime
        return state

    def wait_for_change(self) -> None:
        while True:
            time.sleep(self.poll_interval)
            current = self._snapshot()
            if current != self._snapshots:
                self._snapshots = current
                return


def watch_paths_for_config(config_path: str | Path) -> list[Path]:
    config = load_config(config_path)
    return [
        Path(config_path),
        config.content_dir,
        config.layout_dir,
        config.partial_dir,
        config.static_dir,
    ]


def run_watch(
    config_path: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    serve_site: bool = True,
    live_reload: bool = True,
    debounce_seconds: float = 0.5,
    verbose: bool = False,
    quiet: bool = False,
) -> int:
    reload_state = ReloadState() if live_reload else None
    server_error: list[BaseException] = []

    if serve_site:
        thread = threading.Thread(
            target=_serve_background,
            args=(config_path, host, port, reload_state, server_error),
            daemon=True,
        )
        thread.start()
        time.sleep(0.2)
        if server_error:
            raise server_error[0]

    watcher = DirectoryWatcher(watch_paths_for_config(config_path))

    def trigger_build() -> int:
        from .cli import print_build_summary

        builder = SiteBuilder(
            config_path,
            incremental=True,
            clean_output=False,
            continue_on_error=True,
        )
        try:
            result = builder.build()
        except SSGError as exc:
            logger.error("%s", exc)
            return 1
        if not quiet:
            print_build_summary(result)
        if reload_state is not None:
            reload_state.bump()
        return 0 if result.manifest.pages_failed == 0 and not result.manifest.errors else 1

    exit_code = trigger_build()
    while True:
        try:
            watcher.wait_for_change()
            deadline = time.monotonic() + debounce_seconds
            while time.monotonic() < deadline:
                time.sleep(0.05)
                current = watcher._snapshot()
                if current != watcher._snapshots:
                    watcher._snapshots = current
                    deadline = time.monotonic() + debounce_seconds
            exit_code = trigger_build()
        except KeyboardInterrupt:
            print("Stopping watch")
            return exit_code


def _serve_background(
    config_path: str | Path,
    host: str,
    port: int,
    reload_state: ReloadState | None,
    errors: list[BaseException],
) -> None:
    from .cli import serve

    try:
        serve(str(config_path), host, port, reload_state=reload_state, live_reload=False)
    except BaseException as exc:
        errors.append(exc)
