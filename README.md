# Static Site Generator

A small Python static site generator that reads Markdown files with simple front
matter, converts them to HTML, applies layouts through a template adapter, and
writes static files to `dist/`.

The project is a library plus CLI. There is no Django layer, HTMX layer,
database, admin UI, or live rebuild server.

## Installation

Requires Python 3.11+.

```powershell
pip install -e .
```

That installs the `ssg` package and its single runtime dependency
(`Markdown>=3.0`). For running the test suite, include the optional extra:

```powershell
pip install -e ".[test]"
```

For a fully reproducible install, use the pinned versions in
`requirements.txt` (runtime) and `requirements-dev.txt` (tests, mypy, ruff):

```powershell
pip install -r requirements.txt -r requirements-dev.txt -e .
```

## Quick Start

Build the example site:

```powershell
python -m ssg build --config example_site/site.toml
```

Build with drafts:

```powershell
python -m ssg build --config example_site/site.toml --drafts
```

Skip cleaning `dist/` for this run:

```powershell
python -m ssg build --config example_site/site.toml --no-clean
```

Continue past per-page errors instead of aborting:

```powershell
python -m ssg build --config example_site/site.toml --continue-on-error
```

Override the output directory for one build:

```powershell
python -m ssg build --config example_site/site.toml --output-dir build/preview
```

Create a new content file:

```powershell
python -m ssg new blog/my-post --title "My Post" --config example_site/site.toml
```

Clean the output directory:

```powershell
python -m ssg clean --config example_site/site.toml
```

Serve the built site locally (no rebuild on save):

```powershell
python -m ssg serve --config example_site/site.toml --host 127.0.0.1 --port 8000
```

Print stage-level progress while building:

```powershell
python -m ssg build --config example_site/site.toml --verbose
```

Suppress non-error output (overrides `--verbose`):

```powershell
python -m ssg build --config example_site/site.toml --quiet
```

## Exit codes

| Code | Meaning                                                   |
|------|-----------------------------------------------------------|
| 0    | Success (no failed pages)                                 |
| 1    | Build error — fatal `SSGError`, or partial failure when `--continue-on-error` left `pages_failed > 0` |
| 2    | CLI usage error (`CLIError` — bad path, missing dist, …)   |
| 3    | Unexpected internal error                                  |

## Pipeline

1. Load and validate `site.toml` (warn if optional `partial_dir` / `static_dir` missing)
2. Clean `dist/` safely
3. Discover Markdown files
4. Parse front matter
5. Convert Markdown to HTML
6. Build `Page` models (warn on collection directory slug collisions)
7. Filter drafts
8. Validate layouts for source pages
9. Generate tag and collection pages (shared URL registry)
10. Validate layouts for generated pages
11. Build the final `SiteModel` (recoverable under `--continue-on-error`)
12. Render layouts
13. Write HTML files
14. Copy static assets
15. Write `.ssg-manifest.json`

## Content

Markdown files live in `content/`.

```markdown
---
title: My First Post
date: 2026-05-26
tags: python, static-sites
layout: post.html
draft: false
---

# My First Post

This is Markdown content.
```

Front matter is a small YAML-like key-value format. It is intentionally not full
YAML. Supported fields are `title`, `date`, `tags`, `layout`, `draft`, `slug`,
`description`, and `author`. Unknown fields are kept in `page.metadata` and
surface as build warnings — your templates can still read them via
`{{ page.metadata.<field> }}`.

## Templates

Layouts live in `layouts/`. The fallback template adapter supports variable
interpolation, optional `{% if %}…{% endif %}` blocks, and a `| safe` filter.

```html
<title>{{ page.title }} - {{ site.title }}</title>
<link rel="stylesheet" href="/{{ site.assets_dir }}/css/style.css">
<link rel="canonical" href="{{ page.canonical_url }}">
<main>{{ page.body | safe }}</main>
{% if page.previous_url %}<a href="{{ page.previous_url }}">Previous</a>{% endif %}
```

String values are HTML-escaped by default. Use `| safe` for trusted HTML such
as Markdown body output (`page.body`) and partials (`site.partials.header`).

Partials live in `partials/`, are exposed as `site.partials.<name>`, and are
rendered through the same template engine (so partials may reference
`{{ site.title }}`, etc.). A missing partial reference renders as empty and
is reported in the build warnings.

Supported syntax:

- `{{ page.title }}` — escaped variable interpolation
- `{{ page.body | safe }}` — raw HTML output
- `{% if page.previous_url %}…{% endif %}` — conditional blocks (no `{% else %}`)

Not supported: loops, includes, nested conditionals (nested `{% if %}` raises an
error), or a full template language.

List and dict values (such as `{{ page.tags }}`) render as an escaped Python
repr, not as HTML lists. Use generated listing pages or pre-built HTML instead.

Navigation HTML for top-level `site.nav` nodes is available as `{{ site.nav_html | safe }}`.
In-page links use root-relative paths (`/about/`) so `ssg serve` works locally;
`page.canonical_url` combines `site.base_url` with `page.url` for production
canonical tags.

### Template context reference

Every layout receives this context:

`page`:
- `title`, `url`, `slug`, `layout`, `collection`, `canonical_url`
- `body` (HTML from the Markdown converter — use `| safe`)
- `tags`, `date`, `previous_url`, `next_url`, `generated`
- `metadata` (raw front matter, including unknown fields)

`site`:
- `title`, `base_url`, `assets_dir`, `build_time`
- `pages` (list of page summaries — `title`, `url`, `slug`, `tags`, `date`, `collection`, `previous_url`, `next_url`, `generated`)
- `tags` (`{tag_name: [pages]}`)
- `collections` (`{collection_name: [pages]}`)
- `nav` (tree of `{title, url, children}` nodes)
- `nav_html` (pre-rendered top-level navigation links)
- `partials` (`{partial_name: html}` — pre-rendered partial files)

## Configuration

`site.toml` exposes the following keys (with defaults shown):

```toml
title = "My Static Site"
base_url = "https://example.com"
content_dir = "content"
layout_dir = "layouts"
partial_dir = "partials"
static_dir = "static"
output_dir = "dist"
assets_dir = "assets"
default_layout = "page.html"
permalink = "/{path}/{slug}/"

[build]
drafts = false
clean = true

[scaffold]
post_collections = ["blog"]
```

`permalink` must start with `/` and contain `{slug}`; `{path}` is optional
(useful for flat URL schemes like `/{slug}/`). Unknown placeholders are
rejected at load time. `assets_dir` is the subfolder under `output_dir`
where `static/` is mirrored — defaults to `assets`. `post_collections`
controls which directories under `content/` get the `post.html` layout
when scaffolded with `ssg new`.

`partial_dir` and `static_dir` are optional — if either directory is missing,
the build continues with a warning (empty partials or no copied assets).

## Build manifest

Each build writes `.ssg-manifest.json` to the output directory. The manifest
includes `schema_version` (currently `1`), timing, page counts, warnings,
errors, and a POSIX-formatted list of output files. The `pages_failed` counter
reflects the number of distinct failed pages/inputs, not raw error strings.

## Development

Static type checking runs on the `ssg/` package with mypy (`strict` mode is
not enabled). Tests and lint run via:

```powershell
pip install -r requirements-dev.txt -e .
ruff check ssg tests
mypy ssg
pytest
```

## Scope

Implemented:

- Library core and CLI (`build`, `clean`, `new`, `serve`)
- Clean full rebuild
- Markdown adapter
- Front matter parser with unknown-field warnings
- Page and Site models
- Configurable permalink template
- Tag grouping and generated tag pages
- Collection grouping and generated collection pages
- Navigation tree with URLs on collection nodes
- Previous/next links within dated collections
- Partials at the SSG layer
- Static asset copying
- Build manifest with warnings and errors
- Safety-checked output cleaning
- Continue-on-error mode

Out of scope:

- Incremental builds
- Watch mode
- Live reload
- RSS
- Sitemap
- Asset bundling
- Full YAML parsing
