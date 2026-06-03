""" Static Site Generator Assets """

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .errors import AssetCopyError
from .models import SiteConfig
from .writer import ensure_inside_output

MANIFEST_FILENAME = ".ssg-manifest.json"


def read_manifest_output_files(config: SiteConfig) -> list[str]:
    path = config.output_dir / MANIFEST_FILENAME
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    output_files = data.get("output_files", [])
    if not isinstance(output_files, list):
        return []
    return [str(item) for item in output_files]


def copy_assets(
    config: SiteConfig,
    *,
    skip_if_unchanged: bool = False,
    previous_static_hash: str | None = None,
    current_static_hash: str | None = None,
) -> list[Path]:
    if skip_if_unchanged and previous_static_hash and previous_static_hash == current_static_hash:
        return _list_existing_assets(config)

    if not config.static_dir.exists():
        return []
    if not config.static_dir.is_dir():
        raise AssetCopyError("static path is not a directory", path=config.static_dir)

    copied: list[Path] = []
    target_root = config.output_dir / config.assets_dir
    for source in sorted(config.static_dir.rglob("*")):
        relative = source.relative_to(config.static_dir)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if not source.is_file():
            continue
        target = target_root / relative
        ensure_inside_output(config, target)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        except OSError as exc:
            raise AssetCopyError(str(exc), path=source) from exc
        copied.append(target)
    return copied


def _list_existing_assets(config: SiteConfig) -> list[Path]:
    target_root = config.output_dir / config.assets_dir
    if not target_root.exists():
        return []
    assets: list[Path] = []
    for path in sorted(target_root.rglob("*")):
        if path.is_file():
            assets.append(path)
    return assets
