""" Test Site Model """

from __future__ import annotations

import pytest

from ssg.config import load_config
from ssg.errors import SiteModelError
from ssg.models import Page
from ssg.page_builder import output_path_for_url
from ssg.site_model import build_site_model, generate_derived_pages, generate_tag_pages


def make_page(config, url="/one/", title="One", tags=None, collection=None, date=None):
    return Page(
        source_path=config.content_dir / f"{title}.md",
        relative_source_path=None,
        title=title,
        slug=title.lower(),
        url=url,
        output_path=output_path_for_url(config.output_dir, url),
        layout=config.default_layout,
        date=date,
        tags=tags or [],
        draft=False,
        body_html="<p>body</p>",
        collection=collection,
    )


def test_site_model_detects_duplicate_urls(site_root):
    config = load_config(site_root / "site.toml")
    pages = [make_page(config, "/same/", "One"), make_page(config, "/same/", "Two")]

    with pytest.raises(SiteModelError) as error:
        build_site_model(config, pages)

    message = str(error.value)
    assert "One.md" in message
    assert "Two.md" in message


def test_site_model_groups_tags_and_computes_previous_next(site_root):
    config = load_config(site_root / "site.toml")
    newest = make_page(config, "/blog/new/", "New", ["python"], "blog", "2026-05-27")
    oldest = make_page(config, "/blog/old/", "Old", ["python"], "blog", "2026-05-26")

    site = build_site_model(config, [newest, oldest])

    assert site.tags["python"] == [newest, oldest]
    assert newest.previous_url == "/blog/old/"
    assert oldest.next_url == "/blog/new/"


def test_generate_derived_pages_creates_tag_and_collection_pages(site_root):
    config = load_config(site_root / "site.toml")
    page = make_page(config, "/blog/post/", "Post", ["python"], "blog", "2026-05-26")

    generated = generate_derived_pages(config, [page])

    assert {page.url for page in generated} == {"/tags/python/", "/blog/"}


def test_collection_page_skipped_when_url_already_taken(site_root):
    config = load_config(site_root / "site.toml")
    blog_index = make_page(config, "/blog/", "BlogIndex")
    post = make_page(config, "/blog/post/", "Post", ["python"], "blog", "2026-05-26")
    warnings: list[str] = []

    generated = generate_derived_pages(config, [blog_index, post], warnings)

    assert "/blog/" not in {gen.url for gen in generated}
    assert any("/blog/" in warning for warning in warnings)


def test_prev_next_skipped_for_undated_collection(site_root):
    from ssg.site_model import assign_previous_next

    config = load_config(site_root / "site.toml")
    a = make_page(config, "/blog/a/", "A", collection="blog")
    b = make_page(config, "/blog/b/", "B", collection="blog")
    assign_previous_next({"blog": [a, b]})

    assert a.previous_url is None
    assert a.next_url is None
    assert b.previous_url is None
    assert b.next_url is None


def test_nav_tree_assigns_url_to_collection_index_node(site_root):
    config = load_config(site_root / "site.toml")
    post = make_page(config, "/blog/post/", "Post", collection="blog", date="2026-05-26")
    collection_index = make_page(config, "/blog/", "BlogIndex")
    collection_index.generated = True

    site = build_site_model(config, [post, collection_index])

    blog_node = site.nav_tree.children["blog"]
    assert blog_node.url == "/blog/"


def test_nav_tree_shape(site_root):
    config = load_config(site_root / "site.toml")
    home = make_page(config, "/", "Home")
    about = make_page(config, "/about/", "About")
    post = make_page(config, "/blog/post/", "Post", collection="blog")

    site = build_site_model(config, [home, about, post])

    assert "home" in site.nav_tree.children
    assert "about" in site.nav_tree.children
    assert site.nav_tree.children["about"].url == "/about/"
    assert "blog" in site.nav_tree.children
    assert "post" in site.nav_tree.children["blog"].children


def test_nav_tree_keeps_content_page_url_on_intermediate_node(site_root):
    """An explicit content page at /blog/ should keep its title/URL even when
    a generated collection page also targets /blog/."""
    config = load_config(site_root / "site.toml")
    blog_index = make_page(config, "/blog/", "Blog Home")
    post = make_page(config, "/blog/post/", "Post", collection="blog", date="2026-05-26")

    site = build_site_model(config, [blog_index, post])

    blog_node = site.nav_tree.children["blog"]
    assert blog_node.url == "/blog/"
    assert blog_node.title == "Blog Home"


def test_prev_next_chains_only_dated_subset(site_root):
    from ssg.site_model import assign_previous_next

    config = load_config(site_root / "site.toml")
    new = make_page(config, "/blog/new/", "New", collection="blog", date="2026-05-27")
    old = make_page(config, "/blog/old/", "Old", collection="blog", date="2026-05-26")
    undated = make_page(config, "/blog/wip/", "Wip", collection="blog")

    assign_previous_next({"blog": [new, old, undated]})

    assert new.previous_url == "/blog/old/"
    assert old.next_url == "/blog/new/"
    assert undated.previous_url is None
    assert undated.next_url is None


def test_listing_html_escapes_titles_and_urls(site_root):
    from ssg.site_model import generate_tag_pages

    config = load_config(site_root / "site.toml")
    danger = make_page(
        config, "/blog/x/", '<script>alert("xss")</script>', ["python"], "blog", "2026-05-26"
    )

    [tag_page] = generate_tag_pages(config, [danger])

    assert "<script>" not in tag_page.body_html
    assert "&lt;script&gt;" in tag_page.body_html


def test_tag_slug_collision_skips_second_page(site_root):
    config = load_config(site_root / "site.toml")
    first = make_page(config, "/a/", "A", ["foo bar"], "blog", "2026-05-26")
    second = make_page(config, "/b/", "B", ["foo-bar"], "blog", "2026-05-26")
    warnings: list[str] = []

    generated = generate_tag_pages(config, [first, second], warnings)

    assert len(generated) == 1
    assert generated[0].url == "/tags/foo-bar/"
    assert any("foo-bar" in warning for warning in warnings)
    build_site_model(config, [first, second, *generated], warnings=warnings)


def test_generate_collection_pages_skips_taken_url(site_root):
    from pathlib import Path

    config = load_config(site_root / "site.toml")
    blog_index = make_page(config, url="/blog/", title="Blog", collection="blog")
    blog_index.relative_source_path = Path("blog/index.md")
    post = make_page(config, url="/blog/post/", title="Post", collection="blog")
    post.relative_source_path = Path("blog/post.md")
    warnings: list[str] = []

    pages = generate_derived_pages(config, [blog_index, post], warnings)

    assert not any(page.generated and page.url == "/blog/" for page in pages)
    assert any("collection page" in warning and "already taken" in warning for warning in warnings)
