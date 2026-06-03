""" Static Site Generator Cache """

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .models import SiteConfig

CACHE_FILENAME = ".ssg-cache.json"
CACHE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SiteFingerprints:
    config: str
    layouts: str
    partials: str
    static: str
    content: dict[str, str]

    def global_deps_changed(self, previous: SiteFingerprints | None) -> bool:
        if previous is None:
            return True
        return (
            self.config != previous.config
            or self.layouts != previous.layouts
            or self.partials != previous.partials
        )


def cache_path(config: SiteConfig) -> Path:
    return config.output_dir / CACHE_FILENAME


def file_content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def directory_tree_hash(root: Path) -> str:
    if not root.exists():
        return hashlib.sha256(b"").hexdigest()

    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(file_content_hash(path).encode("utf-8"))
    return digest.hexdigest()


def content_hashes(config: SiteConfig) -> dict[str, str]:
    hashes: dict[str, str] = {}
    if not config.content_dir.exists():
        return hashes
    for path in sorted(config.content_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(config.root_dir).as_posix()
        if any(part.startswith(".") for part in path.relative_to(config.content_dir).parts):
            continue
        if path.suffix.lower() not in {".md", ".markdown"}:
            continue
        hashes[relative] = file_content_hash(path)
    return hashes


def compute_fingerprints(config: SiteConfig, *, config_path: Path) -> SiteFingerprints:
    return SiteFingerprints(
        config=file_content_hash(config_path),
        layouts=directory_tree_hash(config.layout_dir),
        partials=directory_tree_hash(config.partial_dir),
        static=directory_tree_hash(config.static_dir),
        content=content_hashes(config),
    )


def load_cache(config: SiteConfig) -> dict[str, object] | None:
    path = cache_path(config)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None
    return data


def save_cache(
    config: SiteConfig,
    *,
    fingerprints: SiteFingerprints,
    output_files: list[str],
) -> None:
    path = cache_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "config_hash": fingerprints.config,
        "layouts_hash": fingerprints.layouts,
        "partials_hash": fingerprints.partials,
        "static_hash": fingerprints.static,
        "content_hashes": fingerprints.content,
        "last_output_files": output_files,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def fingerprints_from_cache(data: dict[str, object]) -> SiteFingerprints | None:
    try:
        content = data.get("content_hashes", {})
        if not isinstance(content, dict):
            return None
        return SiteFingerprints(
            config=str(data["config_hash"]),
            layouts=str(data["layouts_hash"]),
            partials=str(data["partials_hash"]),
            static=str(data["static_hash"]),
            content={str(key): str(value) for key, value in content.items()},
        )
    except (KeyError, TypeError):
        return None


def prune_stale_outputs(
    config: SiteConfig,
    *,
    previous_files: list[str],
    current_files: set[str],
) -> list[str]:
    removed: list[str] = []
    protected = {CACHE_FILENAME, ".ssg-manifest.json", "sitemap.xml"}
    for relative in previous_files:
        if relative in current_files or relative in protected:
            continue
        target = config.output_dir / relative
        if not target.exists() or not target.is_file():
            continue
        try:
            target.relative_to(config.output_dir.resolve())
        except ValueError:
            continue
        target.unlink()
        removed.append(relative)
        _remove_empty_parents(target.parent, config.output_dir.resolve())
    return removed


def _remove_empty_parents(directory: Path, stop_at: Path) -> None:
    current = directory.resolve()
    stop = stop_at.resolve()
    while current != stop:
        if not current.exists() or not current.is_dir():
            break
        if any(current.iterdir()):
            break
        current.rmdir()
        current = current.parent
