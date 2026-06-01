from __future__ import annotations

import shutil
from pathlib import Path

from .errors import AssetCopyError
from .models import SiteConfig
from .writer import ensure_inside_output


def copy_assets(config: SiteConfig) -> list[Path]:
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
