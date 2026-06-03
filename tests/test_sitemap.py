""" Test Sitemap """

from __future__ import annotations

from ssg.builder import SiteBuilder
from ssg.config import load_config
from ssg.site_model import build_site_model
from ssg.sitemap import render_sitemap, write_sitemap
from tests.test_renderer import make_page


def test_write_sitemap_creates_xml(site_root):
    config = load_config(site_root / "site.toml")
    site = build_site_model(config, [make_page(config)])
    path = write_sitemap(config, site)
    content = path.read_text(encoding="utf-8")

    assert path.name == "sitemap.xml"
    assert "<urlset" in content
    assert "https://example.test/" in content


def test_render_sitemap_skips_drafts(site_root):
    config = load_config(site_root / "site.toml")
    draft = make_page(config)
    draft.url = "/draft/"
    draft.title = "Draft"
    draft.draft = True
    published = make_page(config)
    published.url = "/published/"
    published.title = "Published"
    site = build_site_model(config, [draft, published])

    xml = render_sitemap(config, site)

    assert "/published/" in xml
    assert "/draft/" not in xml


def test_build_writes_sitemap_by_default(site_root):
    SiteBuilder(site_root / "site.toml").build()
    sitemap = site_root / "dist" / "sitemap.xml"
    assert sitemap.exists()


def test_build_can_disable_sitemap(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "clean = true",
            "clean = true\nsitemap = false",
        ),
        encoding="utf-8",
    )
    SiteBuilder(config_path).build()
    assert not (site_root / "dist" / "sitemap.xml").exists()
