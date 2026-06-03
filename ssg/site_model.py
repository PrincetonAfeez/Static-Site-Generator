""" Static Site Generator Site Model """

from __future__ import annotations

import html
from datetime import datetime, timezone

from .errors import SiteModelError
from .models import NavNode, Page, SiteConfig, SiteModel
from .page_builder import output_path_for_url, slugify


def generate_derived_pages(
    config: SiteConfig,
    source_pages: list[Page],
    warnings: list[str] | None = None,
) -> list[Page]:
    taken_urls = {page.url for page in source_pages}
    generated: list[Page] = []
    generated.extend(generate_tag_pages(config, source_pages, warnings, taken_urls))
    generated.extend(generate_collection_pages(config, source_pages, warnings, taken_urls))
    return generated


def build_site_model(
    config: SiteConfig,
    pages: list[Page],
    warnings: list[str] | None = None,
) -> SiteModel:
    collected_warnings = list(warnings) if warnings else []
    pages_by_url = index_pages_by_url(pages)
    tags = group_by_tag(pages)
    collections = group_by_collection(pages)
    assign_previous_next(collections)
    nav_tree = build_nav_tree(pages)
    _attach_intermediate_urls(nav_tree, "", pages_by_url)
    return SiteModel(
        config=config,
        pages=sorted(pages, key=lambda page: page.url),
        pages_by_url=pages_by_url,
        tags=tags,
        collections=collections,
        nav_tree=nav_tree,
        build_time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        warnings=collected_warnings,
    )


def index_pages_by_url(pages: list[Page]) -> dict[str, Page]:
    by_url: dict[str, Page] = {}
    for page in pages:
        existing = by_url.get(page.url)
        if existing is not None:
            first = _source_label(existing)
            second = _source_label(page)
            raise SiteModelError(
                f"duplicate URL {page.url} from {first} and {second}",
                path=page.source_path or page.url,
                conflicting_urls=frozenset({existing.url, page.url}),
            )
        by_url[page.url] = page
    return by_url


def dedupe_pages_by_url(pages: list[Page], warnings: list[str]) -> list[Page]:
    kept: list[Page] = []
    seen: dict[str, Page] = {}
    for page in pages:
        existing = seen.get(page.url)
        if existing is not None:
            warnings.append(
                f"[site-model] skipping duplicate URL {page.url} from "
                f"{_source_label(page)} (keeping {_source_label(existing)})"
            )
            continue
        seen[page.url] = page
        kept.append(page)
    return kept


def group_by_tag(pages: list[Page]) -> dict[str, list[Page]]:
    tags: dict[str, list[Page]] = {}
    for page in pages:
        if page.generated:
            continue
        for tag in page.tags:
            tags.setdefault(tag, []).append(page)
    return {tag: _sort_pages(group) for tag, group in sorted(tags.items())}


def group_by_collection(pages: list[Page]) -> dict[str, list[Page]]:
    collections: dict[str, list[Page]] = {}
    for page in pages:
        if page.generated or not page.collection:
            continue
        collections.setdefault(page.collection, []).append(page)
    return {collection: _sort_pages(group) for collection, group in sorted(collections.items())}


def assign_previous_next(collections: dict[str, list[Page]]) -> None:
    for pages in collections.values():
        # Chain only the dated subset — undated pages are sorted by URL,
        # which has no temporal meaning for "previous"/"next" links.
        dated = [page for page in pages if page.date is not None]
        for index, page in enumerate(dated):
            page.previous_url = dated[index + 1].url if index + 1 < len(dated) else None
            page.next_url = dated[index - 1].url if index > 0 else None


def build_nav_tree(pages: list[Page]) -> NavNode:
    root = NavNode(title="root")
    for page in sorted([page for page in pages if not page.generated], key=lambda item: item.url):
        parts = [part for part in page.url.strip("/").split("/") if part]
        if not parts:
            root.children["home"] = NavNode(title=page.title, url=page.url)
            continue
        current = root
        for part in parts[:-1]:
            current = current.children.setdefault(
                part,
                NavNode(title=part.replace("-", " ").title()),
            )
        current.children[parts[-1]] = NavNode(title=page.title, url=page.url)
    return root


def render_nav_html(node: NavNode) -> str:
    if node.title == "root":
        items = [
            f"<li>{_render_nav_branch(child)}</li>"
            for child in _sorted_nav_children(node)
            if _render_nav_branch(child)
        ]
        if not items:
            return ""
        return "<ul>\n    " + "\n    ".join(items) + "\n  </ul>"
    return _render_nav_branch(node)


def _render_nav_branch(node: NavNode) -> str:
    if node.url:
        label = f'<a href="{html.escape(node.url, quote=True)}">{html.escape(node.title)}</a>'
    elif node.title == "root":
        return ""
    else:
        label = f"<span>{html.escape(node.title)}</span>"
    if not node.children:
        return label
    child_lines = "\n      ".join(
        f"<li>{_render_nav_branch(child)}</li>" for child in _sorted_nav_children(node)
    )
    return f"{label}\n    <ul>\n      {child_lines}\n    </ul>"


def _sorted_nav_children(node: NavNode) -> list[NavNode]:
    return sorted(
        node.children.values(),
        key=lambda child: (child.url is None, child.url or "", child.title),
    )


def _attach_intermediate_urls(node: NavNode, prefix: str, pages_by_url: dict[str, Page]) -> None:
    for key, child in node.children.items():
        path = prefix + key
        candidate_url = f"/{path}/"
        if child.url is None and candidate_url in pages_by_url:
            child.url = candidate_url
        _attach_intermediate_urls(child, path + "/", pages_by_url)


def generate_tag_pages(
    config: SiteConfig,
    source_pages: list[Page],
    warnings: list[str] | None = None,
    taken_urls: set[str] | None = None,
) -> list[Page]:
    pages: list[Page] = []
    tags = group_by_tag(source_pages)
    layout = "tag.html" if (config.layout_dir / "tag.html").exists() else config.default_layout
    if taken_urls is not None:
        reserved_urls = set(taken_urls)
    else:
        reserved_urls = {page.url for page in source_pages}
    for tag, tagged_pages in tags.items():
        url = f"/tags/{slugify(tag)}/"
        if url in reserved_urls:
            if warnings is not None:
                warnings.append(f"skipped generated tag page for '{tag}' — URL {url} already taken")
            continue
        reserved_urls.add(url)
        pages.append(
            Page(
                source_path=None,
                relative_source_path=None,
                title=f"Tag: {tag}",
                slug=slugify(tag),
                url=url,
                output_path=output_path_for_url(config.output_dir, url),
                layout=layout,
                date=None,
                tags=[tag],
                draft=False,
                body_html=_listing_html(f"Posts tagged {tag}", tagged_pages),
                metadata={"tag": tag},
                collection="tags",
                generated=True,
            )
        )
    return pages


def generate_collection_pages(
    config: SiteConfig,
    source_pages: list[Page],
    warnings: list[str] | None = None,
    taken_urls: set[str] | None = None,
) -> list[Page]:
    pages: list[Page] = []
    collections = group_by_collection(source_pages)
    layout = "index.html" if (config.layout_dir / "index.html").exists() else config.default_layout
    if taken_urls is not None:
        reserved_urls = set(taken_urls)
    else:
        reserved_urls = {page.url for page in source_pages}
    for collection, collection_pages in collections.items():
        url = f"/{slugify(collection)}/"
        if url in reserved_urls:
            if warnings is not None:
                warnings.append(
                    f"skipped generated collection page for '{collection}' "
                    f"— URL {url} already taken"
                )
            continue
        reserved_urls.add(url)
        pages.append(
            Page(
                source_path=None,
                relative_source_path=None,
                title=collection.replace("-", " ").title(),
                slug=slugify(collection),
                url=url,
                output_path=output_path_for_url(config.output_dir, url),
                layout=layout,
                date=None,
                tags=[],
                draft=False,
                body_html=_listing_html(collection.replace("-", " ").title(), collection_pages),
                metadata={"collection": collection},
                collection=collection,
                generated=True,
            )
        )
    return pages


def _listing_html(title: str, pages: list[Page]) -> str:
    items = "\n".join(
        f'<li><a href="{html.escape(page.url, quote=True)}">{html.escape(page.title)}</a></li>'
        for page in _sort_pages(pages)
    )
    return f"<h1>{html.escape(title)}</h1>\n<ul>\n{items}\n</ul>"


def _sort_pages(pages: list[Page]) -> list[Page]:
    dated = [page for page in pages if page.date is not None]
    undated = [page for page in pages if page.date is None]
    return sorted(dated, key=lambda page: (page.date or "", page.url), reverse=True) + sorted(
        undated,
        key=lambda page: page.url,
    )


def _source_label(page: Page) -> str:
    if page.source_path is not None:
        return str(page.source_path)
    return f"generated page {page.title!r}"
