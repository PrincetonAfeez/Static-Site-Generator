from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import BuildManifest, SiteConfig
from .writer import ensure_inside_output


def write_manifest(config: SiteConfig, manifest: BuildManifest) -> Path:
    path = config.output_dir / ".ssg-manifest.json"
    ensure_inside_output(config, path)
    path.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")
    return path
