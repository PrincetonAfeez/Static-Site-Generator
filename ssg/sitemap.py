""" Static Site Generator Sitemap """

from __future__ import annotations

import html
from pathlib import Path

from .models import Page, SiteConfig, SiteModel
from .renderer import canonical_url
from .writer import ensure_inside_output


def write_sitemap(config: SiteConfig, site: SiteModel) -> Path:
    path = config.output_dir / "sitemap.xml"
    ensure_inside_output(config, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_sitemap(config, site), encoding="utf-8")
    return path


def render_sitemap(config: SiteConfig, site: SiteModel) -> str:
    urls = sorted(_sitemap_urls(config, site.pages), key=lambda item: item[0])
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{html.escape(loc, quote=True)}</loc>")
        if lastmod:
            lines.append(f"    <lastmod>{html.escape(lastmod, quote=True)}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    lines.append("")
    return "\n".join(lines)


def _sitemap_urls(config: SiteConfig, pages: list[Page]) -> list[tuple[str, str | None]]:
    if not config.base_url.strip():
        return []
    entries: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for page in pages:
        if page.draft:
            continue
        loc = canonical_url(config.base_url, page.url)
        if not loc or loc in seen:
            continue
        seen.add(loc)
        lastmod = page.date if page.date else None
        entries.append((loc, lastmod))
    return entries
