from __future__ import annotations

import dataclasses
import logging
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from .assets import copy_assets
from .config import ensure_safe_output_dir, load_config
from .discovery import discover_content
from .errors import MarkdownConversionError, SiteModelError, SSGError
from .frontmatter import parse_document
from .manifest import write_manifest
from .markdown_adapter import MarkdownConverter
from .models import (
    BuildManifest,
    BuildResult,
    Page,
    RenderedPage,
    SiteConfig,
    SiteModel,
    SourceFile,
)
from .page_builder import build_page, warn_collection_slug_collisions
from .renderer import render_site, validate_page_layouts
from .site_model import build_site_model, generate_derived_pages
from .writer import clean_output_dir, write_pages

logger = logging.getLogger("ssg.build")


class SiteBuilder:
    def __init__(
        self,
        config_path: str | Path = "site.toml",
        *,
        include_drafts: bool | None = None,
        clean_output: bool | None = None,
        output_dir: str | Path | None = None,
        continue_on_error: bool = False,
    ) -> None:
        self.config_path = Path(config_path)
        self.include_drafts = include_drafts
        self.clean_output = clean_output
        self.output_dir_override = Path(output_dir) if output_dir else None
        self.continue_on_error = continue_on_error
        self._converter: MarkdownConverter | None = None

    def build(self) -> BuildResult:
        started = datetime.now(timezone.utc)
        start_time = perf_counter()

        config = self._load_config()
        warnings: list[str] = []
        errors: list[str] = []
        failed_page_keys: set[str] = set()

        self._warn_missing_optional_dirs(config, warnings)

        self._log("clean")
        self._prepare_output(config)

        self._log("discover")
        sources = discover_content(config)

        self._log("parse/convert/page-build")
        source_pages = self._collect_source_pages(
            config, sources, warnings, errors, failed_page_keys
        )

        self._log("filter/generate/site-model")
        site, drafts_skipped, generated_count = self._assemble_site_model(
            config, source_pages, warnings, errors, failed_page_keys
        )

        self._log("render/write/assets")
        rendered_pages, output_files, asset_files = self._render_and_emit(
            config, site, errors, failed_page_keys
        )

        manifest = self._build_manifest(
            config=config,
            started=started,
            start_time=start_time,
            sources=sources,
            rendered_pages=rendered_pages,
            drafts_skipped=drafts_skipped,
            generated_count=generated_count,
            output_files=output_files,
            asset_files=asset_files,
            site=site,
            errors=errors,
            failed_page_keys=failed_page_keys,
        )

        self._log("manifest")
        write_manifest(config, manifest)

        return BuildResult(
            config=config,
            site=site,
            manifest=manifest,
            rendered_pages=rendered_pages,
            asset_files=asset_files,
        )

    def _load_config(self) -> SiteConfig:
        config = load_config(
            self.config_path,
            include_drafts=self.include_drafts,
            clean_output=self.clean_output,
        )
        if self.output_dir_override is not None:
            config = dataclasses.replace(
                config, output_dir=self.output_dir_override.resolve()
            )
            ensure_safe_output_dir(config)
        return config

    def _prepare_output(self, config: SiteConfig) -> None:
        if config.clean_output:
            clean_output_dir(config)
        else:
            config.output_dir.mkdir(parents=True, exist_ok=True)

    def _collect_source_pages(
        self,
        config: SiteConfig,
        sources: list[SourceFile],
        warnings: list[str],
        errors: list[str],
        failed_page_keys: set[str],
    ) -> list[Page]:
        pages: list[Page] = []
        for source in sources:
            try:
                document = parse_document(source)
                warnings.extend(document.warnings)
                try:
                    body_html = self._converter_for(config).convert(document.body_markdown)
                except MarkdownConversionError as exc:
                    raise MarkdownConversionError(exc.message, path=source.path) from exc
                pages.append(build_page(document, body_html, config))
            except SSGError as exc:
                if not self.continue_on_error:
                    raise
                self._record_error(exc, errors, failed_page_keys)
        warn_collection_slug_collisions(pages, warnings)
        return pages

    def _assemble_site_model(
        self,
        config: SiteConfig,
        source_pages: list[Page],
        warnings: list[str],
        errors: list[str],
        failed_page_keys: set[str],
    ) -> tuple[SiteModel, int, int]:
        renderable_pages = [
            page for page in source_pages if config.include_drafts or not page.draft
        ]
        drafts_skipped = len(source_pages) - len(renderable_pages)
        renderable_pages = self._validate_layouts(
            config, renderable_pages, errors, failed_page_keys
        )
        generated_pages = generate_derived_pages(config, renderable_pages, warnings)
        generated_pages = self._validate_layouts(
            config, generated_pages, errors, failed_page_keys
        )
        all_pages = renderable_pages + generated_pages
        try:
            site = build_site_model(config, all_pages, warnings=warnings)
        except SiteModelError as exc:
            if not self.continue_on_error:
                raise
            self._record_error(exc, errors, failed_page_keys)
            site = build_site_model(config, renderable_pages, warnings=warnings)
        return site, drafts_skipped, len(generated_pages)

    def _validate_layouts(
        self,
        config: SiteConfig,
        pages: list[Page],
        errors: list[str],
        failed_page_keys: set[str],
    ) -> list[Page]:
        valid: list[Page] = []
        for page in pages:
            try:
                validate_page_layouts(config, [page])
                valid.append(page)
            except SSGError as exc:
                if not self.continue_on_error:
                    raise
                self._record_error(exc, errors, failed_page_keys, page=page)
        return valid

    def _render_and_emit(
        self,
        config: SiteConfig,
        site: SiteModel,
        errors: list[str],
        failed_page_keys: set[str],
    ) -> tuple[list[RenderedPage], list[Path], list[Path]]:
        if self.continue_on_error:
            rendered_pages = render_site(
                site, errors=errors, failed_page_keys=failed_page_keys
            )
            output_files = write_pages(
                config,
                rendered_pages,
                errors=errors,
                failed_page_keys=failed_page_keys,
            )
        else:
            rendered_pages = render_site(site)
            output_files = write_pages(config, rendered_pages)
        asset_files = copy_assets(config)
        return rendered_pages, output_files, asset_files

    def _build_manifest(
        self,
        *,
        config: SiteConfig,
        started: datetime,
        start_time: float,
        sources: list[SourceFile],
        rendered_pages: list[RenderedPage],
        drafts_skipped: int,
        generated_count: int,
        output_files: list[Path],
        asset_files: list[Path],
        site: SiteModel,
        errors: list[str],
        failed_page_keys: set[str],
    ) -> BuildManifest:
        finished = datetime.now(timezone.utc)
        manifest_path = config.output_dir / ".ssg-manifest.json"
        output_file_names = [
            path.relative_to(config.output_dir).as_posix()
            for path in output_files + asset_files
        ]
        output_file_names.append(
            manifest_path.relative_to(config.output_dir).as_posix()
        )

        return BuildManifest(
            schema_version=1,
            started_at=started.isoformat(timespec="seconds"),
            finished_at=finished.isoformat(timespec="seconds"),
            elapsed_seconds=round(perf_counter() - start_time, 4),
            pages_discovered=len(sources),
            pages_rendered=len(rendered_pages),
            drafts_skipped=drafts_skipped,
            pages_failed=len(failed_page_keys),
            generated_pages=generated_count,
            assets_copied=len(asset_files),
            warnings=list(site.warnings),
            errors=list(errors),
            output_files=output_file_names,
        )

    def _warn_missing_optional_dirs(self, config: SiteConfig, warnings: list[str]) -> None:
        if not config.partial_dir.exists():
            warnings.append(
                f"[config] partial directory not found: {config.partial_dir}"
            )
        if not config.static_dir.exists():
            warnings.append(f"[config] static directory not found: {config.static_dir}")

    def _record_error(
        self,
        exc: SSGError,
        errors: list[str],
        failed_page_keys: set[str],
        *,
        page: Page | None = None,
    ) -> None:
        errors.append(str(exc))
        if page is not None:
            failed_page_keys.add(page.url)
            return
        if exc.path is not None:
            failed_page_keys.add(str(exc.path))
            return
        failed_page_keys.add(str(exc))

    def _converter_for(self, config: SiteConfig) -> MarkdownConverter:
        if self._converter is None:
            self._converter = MarkdownConverter()
        return self._converter

    def _log(self, stage: str) -> None:
        logger.info("[build] %s", stage)
