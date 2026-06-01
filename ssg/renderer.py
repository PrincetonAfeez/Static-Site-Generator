from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .errors import MissingLayoutError, SSGError, TemplateRenderError
from .models import Page, RenderedPage, SiteConfig, SiteModel
from .site_model import render_nav_html
from .template_adapter import TemplateRenderer


PARTIAL_REFERENCE_PATTERN = re.compile(
    r"\{\{\s*site\.partials\.([a-zA-Z0-9_\-]+)\s*(?:\|[^}]*)?\}\}"
)


def render_site(
    site: SiteModel,
    template_renderer: TemplateRenderer | None = None,
    *,
    errors: list[str] | None = None,
    failed_page_keys: set[str] | None = None,
) -> list[RenderedPage]:
    renderer = template_renderer or TemplateRenderer()
    try:
        partials = load_partials(site.config.partial_dir)
    except TemplateRenderError as exc:
        if errors is None:
            raise
        errors.append(str(exc))
        partials = {}
    seen_warnings = set(site.warnings)
    layout_cache: dict[str, str] = {}
    rendered: list[RenderedPage] = []
    for page in site.pages:
        try:
            rendered.append(
                render_page(page, site, renderer, partials, layout_cache, seen_warnings)
            )
        except SSGError as exc:
            if errors is None:
                raise
            errors.append(str(exc))
            if failed_page_keys is not None:
                failed_page_keys.add(page.url)
    return rendered


def render_page(
    page: Page,
    site: SiteModel,
    renderer: TemplateRenderer,
    partials: dict[str, str],
    layout_cache: dict[str, str] | None = None,
    seen_warnings: set[str] | None = None,
) -> RenderedPage:
    layout_path = site.config.layout_dir / page.layout
    # Defense-in-depth: layouts are validated earlier in SiteBuilder, but
    # render_page may also be called directly without that pass.
    if not layout_path.exists():
        source = page.source_path or page.url
        raise MissingLayoutError(
            f'missing layout "{page.layout}" for page {page.url}',
            path=source,
        )

    try:
        if layout_cache is not None and page.layout in layout_cache:
            layout_text = layout_cache[page.layout]
        else:
            layout_text = layout_path.read_text(encoding="utf-8")
            if layout_cache is not None:
                layout_cache[page.layout] = layout_text
        _warn_unknown_partials(layout_text, page.layout, partials, site.warnings, seen_warnings)
        context = build_context(page, site, partials)
        context["site"] = {
            **context["site"],
            "partials": prerender_partials(renderer, partials, context),
        }
        html = renderer.render(layout_text, context)
    except MissingLayoutError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        source = page.source_path or page.url
        raise TemplateRenderError(str(exc), path=source) from exc
    return RenderedPage(page=page, html=html)


def prerender_partials(
    renderer: TemplateRenderer,
    partials: dict[str, str],
    context: dict[str, Any],
) -> dict[str, str]:
    if not partials:
        return {}
    rendered = dict(partials)
    limit = len(partials) + 1
    for _ in range(limit):
        prior = rendered
        partial_context = {
            **context,
            "site": {**context["site"], "partials": rendered},
        }
        rendered = {
            name: renderer.render(content, partial_context) for name, content in partials.items()
        }
        if rendered == prior:
            return rendered
    raise TemplateRenderError("partial template references did not stabilize")


def _warn_unknown_partials(
    layout_text: str,
    layout_name: str,
    partials: dict[str, str],
    warnings: list[str],
    seen: set[str] | None = None,
) -> None:
    seen = seen if seen is not None else set(warnings)
    for match in PARTIAL_REFERENCE_PATTERN.finditer(layout_text):
        name = match.group(1)
        if name in partials:
            continue
        message = f"layout {layout_name} references unknown partial '{name}'"
        if message in seen:
            continue
        seen.add(message)
        warnings.append(message)


def build_context(page: Page, site: SiteModel, partials: dict[str, str]) -> dict[str, Any]:
    return {
        "page": {
            "title": page.title,
            "url": page.url,
            "slug": page.slug,
            "body": page.body_html,
            "tags": page.tags,
            "date": page.date,
            "layout": page.layout,
            "metadata": page.metadata,
            "collection": page.collection,
            "previous_url": page.previous_url,
            "next_url": page.next_url,
            "generated": page.generated,
            "draft": page.draft,
            "canonical_url": canonical_url(site.config.base_url, page.url),
        },
        "site": {
            "title": site.config.title,
            "base_url": site.config.base_url,
            "assets_dir": site.config.assets_dir,
            "pages": [page_to_context(item) for item in site.pages],
            "tags": {
                tag: [page_to_context(item) for item in pages] for tag, pages in site.tags.items()
            },
            "collections": {
                name: [page_to_context(item) for item in pages]
                for name, pages in site.collections.items()
            },
            "nav": nav_to_context(site.nav_tree),
            "nav_html": render_nav_html(site.nav_tree),
            "build_time": site.build_time,
            "partials": partials,
        },
    }


def canonical_url(base_url: str, page_url: str) -> str:
    base = base_url.rstrip("/")
    if not base:
        return page_url
    return f"{base}{page_url}"


def page_to_context(page: Page) -> dict[str, Any]:
    return {
        "title": page.title,
        "url": page.url,
        "slug": page.slug,
        "tags": page.tags,
        "date": page.date,
        "collection": page.collection,
        "previous_url": page.previous_url,
        "next_url": page.next_url,
        "generated": page.generated,
    }


def nav_to_context(node: Any) -> dict[str, Any]:
    return {
        "title": node.title,
        "url": node.url,
        "children": {key: nav_to_context(child) for key, child in node.children.items()},
    }


def validate_page_layouts(config: SiteConfig, pages: list[Page]) -> None:
    for page in pages:
        layout_path = config.layout_dir / page.layout
        if layout_path.exists():
            continue
        source = page.source_path or page.url
        raise MissingLayoutError(
            f'missing layout "{page.layout}" for page {page.url}',
            path=source,
        )


def load_partials(partial_dir: Path) -> dict[str, str]:
    if not partial_dir.exists():
        return {}
    partials: dict[str, str] = {}
    for path in sorted(partial_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(partial_dir)
        if any(part.startswith(".") for part in relative.parts):
            continue
        key = path.stem
        if key in partials:
            raise TemplateRenderError(
                f"duplicate partial name '{key}'",
                path=path,
            )
        partials[key] = path.read_text(encoding="utf-8")
    return partials
