""" Test Manifest Module """

from __future__ import annotations

import json

from ssg.config import load_config
from ssg.manifest import write_manifest
from ssg.models import BuildManifest


def test_write_manifest_persists_json(site_root):
    config = load_config(site_root / "site.toml")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = BuildManifest(
        schema_version=1,
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:01+00:00",
        elapsed_seconds=1.0,
        pages_discovered=1,
        pages_rendered=1,
        drafts_skipped=0,
        pages_failed=0,
        generated_pages=0,
        assets_copied=0,
        warnings=[],
        errors=[],
        output_files=["index.html"],
    )

    path = write_manifest(config, manifest)

    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["pages_discovered"] == 1
    assert data["output_files"] == ["index.html"]
