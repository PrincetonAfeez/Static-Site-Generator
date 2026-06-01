from __future__ import annotations

import shutil
from pathlib import Path

from .config import ensure_safe_output_dir
from .errors import OutputWriteError
from .models import RenderedPage, SiteConfig


def clean_output_dir(config: SiteConfig) -> None:
    ensure_safe_output_dir(config)
    if config.output_dir.exists():
        shutil.rmtree(config.output_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)


def remove_output_dir(config: SiteConfig) -> None:
    ensure_safe_output_dir(config)
    if config.output_dir.exists():
        shutil.rmtree(config.output_dir)


def write_pages(
    config: SiteConfig,
    rendered_pages: list[RenderedPage],
    *,
    errors: list[str] | None = None,
    failed_page_keys: set[str] | None = None,
) -> list[Path]:
    written: list[Path] = []
    for rendered in rendered_pages:
        try:
            path = rendered.page.output_path
            ensure_inside_output(config, path)
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(rendered.html, encoding="utf-8")
            except OSError as exc:
                raise OutputWriteError(str(exc), path=path) from exc
            written.append(path)
        except OutputWriteError as exc:
            if errors is None:
                raise
            errors.append(str(exc))
            if failed_page_keys is not None:
                failed_page_keys.add(rendered.page.url)
    return written


def ensure_inside_output(config: SiteConfig, path: Path) -> None:
    output = config.output_dir.resolve()
    target = path.resolve()
    try:
        target.relative_to(output)
    except ValueError as exc:
        raise OutputWriteError("refusing to write outside output_dir", path=target) from exc
