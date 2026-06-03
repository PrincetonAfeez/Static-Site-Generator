# Architecture Decision Record
## App — Static Site Generator
**Publishing Pipeline Group | Document 1 of 5**
**Status: Accepted**

---

## Context

The Publishing Pipeline group requires a small Python static site generator that reads Markdown files with YAML front matter, converts content into HTML, applies layouts through a deliberately small template adapter, and writes a complete static site to an output directory.

The project is a library plus CLI. It is not a Django app, not a database-backed CMS, not an HTMX app, and not a live rebuild server. Its purpose is to demonstrate a staged build pipeline, safe filesystem behavior, content modeling, template rendering boundaries, static asset copying, manifest generation, sitemap generation, scaffolding, watch mode, and incremental build cache behavior.

The selected architecture centers on `SiteBuilder`. The builder orchestrates the pipeline but delegates each stage to focused modules:

```text
config → discovery → frontmatter → markdown → page model → site model
      → render → write pages → copy assets → sitemap → manifest → cache
```

---

## Decisions

### Decision 1 — Use a staged build pipeline

**Chosen:** Implement the generator as a staged pipeline coordinated by `SiteBuilder`.

**Rejected:** A single monolithic `build()` function that reads, parses, renders, and writes everything inline.

**Reason:** Static-site generation has many boundaries: configuration, discovery, parsing, page construction, rendering, output safety, and manifests. Staging makes failures attributable and makes each phase independently testable.

---

### Decision 2 — Use TOML for site configuration

**Chosen:** Load `site.toml` using standard-library `tomllib`.

**Rejected:** YAML or Python config files.

**Reason:** TOML is readable for simple site configuration, available in Python 3.11+, and keeps config parsing separate from executable code.

---

### Decision 3 — Use Markdown plus YAML front matter

**Chosen:** Content files are Markdown with optional YAML front matter.

**Rejected:** HTML-only content, JSON metadata, or a custom metadata parser.

**Reason:** Markdown is the expected authoring format for small static sites. YAML front matter supports strings, booleans, dates, lists, and multiline values while remaining familiar to static-site workflows.

---

### Decision 4 — Preserve unknown front matter as metadata with warnings

**Chosen:** Unknown front matter fields are retained in `page.metadata` and surfaced as warnings.

**Rejected:** Failing the build on unknown fields or silently discarding them.

**Reason:** Templates may intentionally use custom metadata. Warning rather than failing provides flexibility while still alerting the author to non-standard fields.

---

### Decision 5 — Keep the template adapter intentionally small

**Chosen:** Support variable interpolation, optional `{% if %}` blocks, and `| safe`.

**Rejected:** Full Jinja compatibility, loops, includes, macros, nested conditionals, or arbitrary Python expressions.

**Reason:** The generator needs enough templating to render layouts safely, not a full template-language implementation. The small adapter keeps behavior inspectable and limits execution risk.

---

### Decision 6 — Escape template values by default

**Chosen:** Template values are HTML-escaped unless marked with `| safe`.

**Rejected:** Raw interpolation by default.

**Reason:** Static output still has XSS concerns when untrusted content is inserted into layouts. Markdown body output and trusted partials can be explicitly marked safe.

---

### Decision 7 — Model pages and the site explicitly

**Chosen:** Use typed dataclasses: `SiteConfig`, `SourceFile`, `ParsedDocument`, `Page`, `SiteModel`, `RenderedPage`, `BuildManifest`, and `BuildResult`.

**Rejected:** Passing unstructured dictionaries through the pipeline.

**Reason:** The site generator has many data transitions. Typed models make the contract of each stage clear.

---

### Decision 8 — Generate tag and collection pages at the site-model layer

**Chosen:** Build source pages first, then generate derived tag and collection pages with a shared URL registry.

**Rejected:** Treating generated listing pages as content files or generating them during rendering.

**Reason:** Generated pages need to participate in duplicate URL detection, navigation, manifests, and rendering like normal pages. The site-model stage is the right point to attach them.

---

### Decision 9 — Validate output directory safety aggressively

**Chosen:** Ensure `output_dir` is inside the site root, not the site root itself, not protected content/layout/static/partial/home directories, and not a filesystem root.

**Rejected:** Trusting arbitrary configured output paths.

**Reason:** The build command can clean the output directory. A bad path could delete source content or user files. Safety checks are required before cleaning or writing.

---

### Decision 10 — Support continue-on-error mode

**Chosen:** `--continue-on-error` records recoverable page/render/write/asset errors in the manifest and continues when possible.

**Rejected:** Always aborting on the first page-level error.

**Reason:** Portfolio-grade tooling should support partial builds for debugging. Fatal configuration and unrecoverable errors still fail normally.

---

### Decision 11 — Add incremental builds with fingerprints

**Chosen:** Incremental mode stores `.ssg-cache.json` with config/layout/partial/static/content hashes and prunes stale outputs from the previous manifest.

**Rejected:** Full clean rebuild only.

**Reason:** Full rebuild is simpler and remains the default, but incremental mode demonstrates cache invalidation, content fingerprints, and stale-output pruning.

---

### Decision 12 — Implement watch/serve locally without external dependencies

**Chosen:** Use a polling watcher and `ThreadingHTTPServer` with optional live-reload polling.

**Rejected:** Watchdog dependency, Node dev server, or browser websocket infrastructure.

**Reason:** The local preview server should remain simple and Python-native. Polling is sufficient for an academic static generator and avoids adding a cross-platform filesystem watcher dependency.

---

## Consequences

**Positive:**
- Build stages are testable and explainable.
- Content parsing, page modeling, site modeling, rendering, and writing stay separated.
- The CLI and library share the same `SiteBuilder` implementation.
- Output cleaning is guarded against destructive paths.
- Static output includes manifest and optional sitemap artifacts.
- Incremental mode demonstrates cache design without replacing the default clean build.
- Watch mode gives a practical local authoring loop.
- Template escaping is secure by default.

**Negative / Trade-offs:**
- The template adapter is intentionally limited.
- Watch mode is polling-based rather than event-driven.
- Incremental build still rebuilds site structure when global dependencies change.
- No RSS feed support.
- No asset bundling or minification.
- No database, admin UI, plugin system, or full CMS layer.
- The `| safe` filter places trust responsibility on the template author.

---

## Alternatives Not Explored

- Jinja2 integration.
- Full custom template language.
- YAML or Python site config.
- Markdown extensions configurable from TOML.
- RSS feed generation.
- Asset bundling/minification.
- Remote publishing/deploy commands.
- Watchdog-based filesystem events.
- Plugin architecture.
- Database-backed content management.

---

*Constitution reference: Article 1 (Python fundamentals and architectural thinking), Article 3.3 (scope discipline), Article 4 (quality proportional to scope), Article 5 (trade-off documentation), Article 6 (verification), and Article 7 (progressive complexity).*

---


# Technical Design Document
## App — Static Site Generator
**Publishing Pipeline Group | Document 2 of 5**

---

## Overview

Static Site Generator is a Python package and CLI that converts Markdown content into a static HTML website.

**Package:** `ssg`  
**Console script:** `ssg`  
**Python requirement:** `>=3.11`  
**Runtime dependencies:** `Markdown>=3.0`, `PyYAML>=6.0`  
**Main API:** `SiteBuilder`, `load_config`  
**Main CLI commands:** `build`, `clean`, `new`, `serve`, `watch`

---

## Build Flow

```text
ssg build
  │
  ▼
SiteBuilder.build()
  │
  ├── load_config(site.toml)
  ├── warn on missing optional partial/static dirs
  ├── read prior manifest/cache if incremental
  ├── compute fingerprints
  ├── clean or create output_dir
  ├── discover Markdown sources
  ├── parse YAML front matter
  ├── convert Markdown to HTML
  ├── build Page dataclasses
  ├── filter drafts
  ├── validate source-page layouts
  ├── generate tag and collection pages
  ├── validate generated-page layouts
  ├── build SiteModel
  ├── render layouts and partials
  ├── write HTML pages
  ├── copy static assets
  ├── write sitemap.xml when enabled
  ├── write .ssg-manifest.json
  ├── prune stale outputs in incremental mode
  └── save .ssg-cache.json
```

---

## Module-Level Structure

```text
Static-Site-Generator/
  ssg/
    __init__.py
    assets.py
    builder.py
    cache.py
    cli.py
    config.py
    discovery.py
    errors.py
    frontmatter.py
    manifest.py
    markdown_adapter.py
    models.py
    page_builder.py
    renderer.py
    scaffold.py
    site_model.py
    sitemap.py
    template_adapter.py
    watch.py
    writer.py
  example_site/
    site.toml
    content/
    layouts/
    partials/
    static/
  docs/
  tests/
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  Makefile
  scripts/
```

---

## Module Dependency Graph

```text
cli.py
  ├── SiteBuilder
  ├── load_config
  ├── scaffold_content
  ├── remove_output_dir
  ├── run_watch
  └── serve helpers

builder.py
  ├── assets
  ├── cache
  ├── config
  ├── discovery
  ├── frontmatter
  ├── manifest
  ├── markdown_adapter
  ├── page_builder
  ├── renderer
  ├── site_model
  ├── sitemap
  └── writer

renderer.py
  ├── template_adapter
  ├── site_model.render_nav_html
  └── models

site_model.py
  ├── page_builder.output_path_for_url
  └── Page / SiteModel / NavNode

writer.py
  ├── config.ensure_safe_output_dir
  └── errors.OutputWriteError
```

---

## Core Data Structures

### `SiteConfig`

Holds resolved configuration:
- `root_dir`
- `title`
- `base_url`
- `content_dir`
- `layout_dir`
- `partial_dir`
- `static_dir`
- `output_dir`
- `default_layout`
- `permalink`
- `include_drafts`
- `clean_output`
- `incremental`
- `generate_sitemap`
- `post_collections`
- `assets_dir`

---

### `SourceFile`

Represents a discovered Markdown source file:
- absolute `path`
- `relative_path` under `content_dir`
- file `extension`

---

### `ParsedDocument`

Represents one source file after front matter parsing:
- source metadata
- normalized front matter dictionary
- Markdown body
- raw text
- warnings

---

### `Page`

Represents one renderable page:
- source path
- title
- slug
- URL
- output path
- layout
- date
- tags
- draft flag
- HTML body
- metadata
- collection
- generated flag
- previous/next links

---

### `SiteModel`

Represents the complete site graph:
- config
- pages
- pages by URL
- tags
- collections
- navigation tree
- build timestamp
- warnings

---

### `BuildManifest`

Represents build telemetry:
- schema version
- start/finish time
- elapsed seconds
- page counts
- generated-page count
- asset count
- warnings/errors
- output file list
- incremental flag
- stale-files-removed count

---

## Function Reference

### `load_config()`

Reads and validates TOML configuration. Applies optional CLI overrides for drafts, clean output, and incremental mode.

Validation includes:
- config path exists and is a file
- title and default layout are not empty
- permalink starts with `/`
- permalink includes `{slug}`
- permalink placeholders are limited to `{path}` and `{slug}`
- assets directory is relative and cannot contain `..`
- content/layout directories exist
- output directory is safe

---

### `discover_content()`

Recursively discovers `.md` and `.markdown` files under `content_dir`, skipping hidden path parts and sorting by POSIX relative path.

---

### `parse_document()`

Reads a Markdown file, splits optional front matter, parses YAML metadata, normalizes supported fields, and returns `ParsedDocument`.

Supported front matter fields:
- `title`
- `date`
- `tags`
- `layout`
- `draft`
- `slug`
- `description`
- `author`

---

### `MarkdownConverter.convert()`

Uses Python-Markdown with the `extra` extension by default and converts Markdown text to HTML.

---

### `build_page()`

Creates a `Page` from a `ParsedDocument` and converted body HTML.

Responsibilities:
- validate slug does not contain traversal or separators
- derive slug
- derive title
- derive collection
- derive URL from permalink
- derive output path
- attach layout/date/tags/draft/body/metadata

---

### `generate_derived_pages()`

Creates generated tag pages and collection pages after source pages exist.

Derived page behavior:
- generated tag pages live under `/tags/<tag>/`
- generated collection pages live under `/<collection>/`
- generated pages use `tag.html`, `index.html`, or the default layout depending on availability
- URL collisions are skipped with warnings

---

### `build_site_model()`

Indexes pages by URL, groups by tag and collection, assigns previous/next links inside dated collections, builds navigation, attaches intermediate navigation URLs, and returns `SiteModel`.

---

### `render_site()`

Loads partials, caches layout text, builds a context per page, pre-renders partials, renders layouts, records recoverable errors when requested, and returns `RenderedPage` objects.

---

### `TemplateRenderer.render()`

Supports:
- `{{ dotted.path }}`
- `{{ dotted.path | safe }}`
- `{% if dotted.path %}...{% endif %}`

Rules:
- non-safe interpolation is escaped
- missing values render empty
- nested conditionals raise `TemplateRenderError`
- lists/dicts render as escaped Python repr unless safe

---

### `write_pages()`

Writes rendered HTML to disk after verifying every target path remains inside `output_dir`.

---

### `copy_assets()`

Copies files from `static_dir` to `output_dir / assets_dir`, skipping hidden path segments and optionally reusing existing copied assets when static fingerprints are unchanged.

---

### `write_sitemap()`

Writes `sitemap.xml` if enabled and `base_url` is present. Drafts are excluded.

---

### `write_manifest()`

Writes `.ssg-manifest.json` using `dataclasses.asdict()` and JSON formatting.

---

### `save_cache()` / `load_cache()`

Persists and reads `.ssg-cache.json` for incremental builds.

---

## Error Handling Strategy

The error hierarchy uses stage-tagged exceptions:
- `ConfigError`
- `DiscoveryError`
- `FrontMatterError`
- `MarkdownConversionError`
- `PageBuildError`
- `SiteModelError`
- `TemplateRenderError`
- `MissingLayoutError`
- `OutputWriteError`
- `AssetCopyError`
- `CLIError`

CLI exit codes:
- `0`: success
- `1`: build error or `SSGError`
- `2`: CLI usage/configuration error
- `3`: unexpected internal error

---

## Known Limits

- No full Jinja syntax.
- No loops/includes/macros in templates.
- No nested conditionals.
- No RSS feeds.
- No asset bundling/minification.
- No plugin architecture.
- Watch mode uses polling.
- Incremental mode is hash based and still dependent on global dependency checks.

---

## Verification Summary

The package configuration enforces:
- pytest test discovery under `tests`
- coverage source as `ssg`
- coverage fail-under of 97
- mypy strict mode for `ssg`
- Ruff linting and format checks
- CI on Ubuntu and Windows for Python 3.11, 3.12, and 3.13

---

*Constitution reference: Article 4 (engineering quality), Article 6 (behavior verification), Article 7 (progressive complexity), and Article 8 (valid learner work).*

---


# Interface Design Specification
## App — Static Site Generator
**Publishing Pipeline Group | Document 3 of 5**

---

## Public Python Interface

### Import

```python
from ssg import SiteBuilder, load_config
```

Additional exported names include:
- `BuildManifest`
- `BuildResult`
- `Page`
- `ParsedDocument`
- `RenderedPage`
- `SiteConfig`
- `SiteModel`
- `SourceFile`
- `SSGError` and specialized error types

---

## Library Usage

```python
from ssg import SiteBuilder, load_config

result = SiteBuilder("site.toml", continue_on_error=True).build()
print(result.manifest.pages_rendered)

config = load_config("site.toml", include_drafts=True)
print(config.output_dir)
```

---

## `SiteBuilder` Contract

```python
SiteBuilder(
    config_path="site.toml",
    *,
    include_drafts=None,
    clean_output=None,
    output_dir=None,
    continue_on_error=False,
    incremental=None,
)
```

### `build() -> BuildResult`

Builds the full site and returns:
- resolved config
- final site model
- build manifest
- rendered pages
- copied asset files

Raises `SSGError` subclasses unless `continue_on_error` converts recoverable failures into manifest errors.

---

## CLI Interface

### Version

```powershell
ssg --version
python -m ssg --version
```

---

### Build

```powershell
ssg build --config example_site/site.toml
```

Options:

| Option | Description |
|---|---|
| `--config PATH` | Site TOML path |
| `--drafts` / `--no-drafts` | Include or exclude drafts |
| `--clean` / `--no-clean` | Clean output before build |
| `--incremental` | Skip cleaning, use cache, prune stale outputs |
| `--verbose` | Print stage-level logging |
| `--quiet` | Suppress non-error output |
| `--continue-on-error` | Skip recoverable failed pages |
| `--output-dir PATH` | Override configured output directory |

---

### Clean

```powershell
ssg clean --config example_site/site.toml
```

Removes the configured output directory after safety validation.

---

### New

```powershell
ssg new blog/my-post --title "My Post" --config example_site/site.toml
```

Creates a Markdown file under `content_dir` with front matter.

Rules:
- path must be relative
- path must be `.md`, `.markdown`, or have no suffix
- file must stay inside `content_dir`
- existing file is not overwritten
- blog/post collection paths can receive `post.html` layout

---

### Serve

```powershell
ssg serve --config example_site/site.toml --host 127.0.0.1 --port 8000
ssg serve --config example_site/site.toml --live-reload
```

Serves built `dist/` locally using Python's threaded HTTP server.

---

### Watch

```powershell
ssg watch --config example_site/site.toml
ssg watch --config example_site/site.toml --no-serve
ssg watch --config example_site/site.toml --no-live-reload
```

Watches config, content, layouts, partials, and static files. Rebuilds incrementally after debounce and optionally serves with browser reload polling.

---

## Configuration Contract

Example:

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
incremental = false
sitemap = true

[scaffold]
post_collections = ["blog"]
```

Validation rules:
- `permalink` must start with `/`
- `permalink` must include `{slug}`
- only `{path}` and `{slug}` placeholders are allowed
- `assets_dir` must be relative and must not contain `..`
- `output_dir` must be safe to clean/write

---

## Content Contract

Markdown file with front matter:

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

Supported front matter fields:
- `title`
- `date`
- `tags`
- `layout`
- `draft`
- `slug`
- `description`
- `author`

Unknown fields:
- preserved in `page.metadata`
- reported as build warnings

---

## Template Contract

Supported syntax:

```html
{{ page.title }}
{{ page.body | safe }}
{% if page.previous_url %}<a href="{{ page.previous_url }}">Previous</a>{% endif %}
```

Rules:
- values are HTML-escaped by default
- `| safe` bypasses escaping
- missing values render empty
- only `if` blocks are supported
- no `else`
- no loops
- no includes
- no nested conditionals
- only `safe` is supported as a filter

---

## Template Context

### `page`

Includes:
- `title`
- `url`
- `slug`
- `layout`
- `collection`
- `canonical_url`
- `body`
- `tags`
- `date`
- `draft`
- `previous_url`
- `next_url`
- `generated`
- `metadata`

### `site`

Includes:
- `title`
- `base_url`
- `assets_dir`
- `build_time`
- `pages`
- `tags`
- `collections`
- `nav`
- `nav_html`
- `partials`

---

## Output Contract

A successful build may write:
- HTML files under `dist/`
- copied static assets under `dist/<assets_dir>/`
- `sitemap.xml` when enabled and `base_url` is present
- `.ssg-manifest.json`
- `.ssg-cache.json` for incremental builds

---

## Manifest Contract

`.ssg-manifest.json` includes:
- `schema_version`
- `started_at`
- `finished_at`
- `elapsed_seconds`
- `pages_discovered`
- `pages_rendered`
- `drafts_skipped`
- `pages_failed`
- `generated_pages`
- `assets_copied`
- `warnings`
- `errors`
- `output_files`
- `incremental`
- `stale_files_removed`

---

## Exit Codes

| Code | Meaning |
|---:|---|
| `0` | Success |
| `1` | Build error or recoverable errors remained in manifest |
| `2` | CLI usage/configuration error |
| `3` | Unexpected internal error |

---

## Side Effects

| Operation | Side Effect |
|---|---|
| `build` | Writes static site output, manifest, cache, sitemap |
| `clean` | Removes output directory after safety validation |
| `new` | Creates a Markdown content file |
| `serve` | Starts local HTTP server |
| `watch` | Rebuilds repeatedly and may start local HTTP server |
| `load_config` | Reads TOML configuration |
| `parse_document` | Reads source Markdown files |

---

*Constitution reference: Article 4 (input/output boundaries), Article 6 (verification), and Article 8 (understandable and verifiable work).*

---


# Runbook
## App — Static Site Generator
**Publishing Pipeline Group | Document 4 of 5**

---

## Requirements

### Runtime

- Python 3.11 or newer
- Markdown `>=3.0`
- PyYAML `>=6.0`

### Development

- pytest
- pytest-cov
- mypy
- ruff

---

## Installation

### Editable install

```powershell
pip install -e .
```

### Test install

```powershell
pip install -e ".[test]"
```

### Reproducible install

```powershell
pip install -r requirements.txt -r requirements-dev.txt -e .
```

---

## First Build

```powershell
python -m ssg build --config example_site/site.toml
```

Expected:
```text
Built site successfully.
```

Open the generated site:

```powershell
python -m ssg serve --config example_site/site.toml --host 127.0.0.1 --port 8000
```

---

## Standard Operating Procedures

### Build with drafts

```powershell
python -m ssg build --config example_site/site.toml --drafts
```

---

### Incremental build

```powershell
python -m ssg build --config example_site/site.toml --incremental
```

Expected:
- output directory is not cleaned first
- stale files from prior manifest may be pruned
- `.ssg-cache.json` is updated

---

### Build without cleaning

```powershell
python -m ssg build --config example_site/site.toml --no-clean
```

---

### Continue after recoverable page errors

```powershell
python -m ssg build --config example_site/site.toml --continue-on-error
```

Expected:
- build may finish with manifest errors
- CLI returns `1` if pages failed or manifest errors remain

---

### Create new content

```powershell
python -m ssg new blog/my-post --title "My Post" --config example_site/site.toml
```

---

### Clean output

```powershell
python -m ssg clean --config example_site/site.toml
```

---

### Serve built site

```powershell
python -m ssg serve --config example_site/site.toml --host 127.0.0.1 --port 8000
```

---

### Watch and live reload

```powershell
python -m ssg watch --config example_site/site.toml
```

---

## Quality Checks

### Ruff

```powershell
ruff check ssg tests
ruff format --check ssg tests
```

### Mypy

```powershell
mypy ssg
mypy tests --explicit-package-bases
```

### Tests and coverage

```powershell
pytest --cov=ssg --cov-report=term-missing --cov-fail-under=97
```

### Full local gate

```powershell
.\scripts\check.ps1
```

or:

```powershell
make check
```

---

## Health Checks

### Package import

```powershell
python -c "from ssg import SiteBuilder, load_config; print('ok')"
```

Expected:
```text
ok
```

---

### CLI version

```powershell
ssg --version
```

Expected:
```text
ssg 0.4.0
```

---

### Build summary

```powershell
ssg build --config example_site/site.toml
```

Expected:
- pages discovered count
- pages rendered count
- generated pages count
- drafts skipped count
- assets copied count
- output path
- elapsed time

---

### Manifest check

After build:

```powershell
Get-Content example_site/dist/.ssg-manifest.json
```

Expected:
- JSON manifest exists
- `schema_version` is `1`
- `errors` is empty for successful build

---

## Known Failure Modes

### Config file missing

**Symptom:**
```text
[config] site.toml: config file not found
```

**Fix:**
Use `--config` with the correct file path.

---

### Content or layout directory missing

**Symptom:**
```text
[config] ... content directory not found
[config] ... layout directory not found
```

**Fix:**
Create the configured directories or correct `site.toml`.

---

### Unsafe output directory

**Cause:** `output_dir` points outside site root, to the site root, a protected directory, home directory, or filesystem root.

**Fix:**
Use a relative safe output directory such as `dist`.

---

### Invalid front matter

**Common causes:**
- missing closing `---`
- YAML is not a mapping
- non-string metadata key
- invalid `draft` boolean
- invalid `date`
- non-string tag entries

**Fix:**
Correct the YAML block in the content file.

---

### Missing layout

**Symptom:**
```text
[render] ... missing layout "post.html" for page /blog/post/
```

**Fix:**
Create the layout file or change the page front matter to an existing layout.

---

### Nested conditional in template

**Symptom:**
```text
[render] nested {% if %} blocks are not supported
```

**Fix:**
Flatten the template or precompute HTML/content in Markdown or generated pages.

---

### Serve before build

**Symptom:**
```text
[cli] ... output directory does not exist; run build first
```

**Fix:**
Run `ssg build` first.

---

## Troubleshooting Decision Tree

```text
Build failed
  ├── Config error?
  │     ├── Check site.toml path
  │     ├── Check content/layout directories
  │     ├── Check permalink format
  │     └── Check output_dir safety
  ├── Front matter error?
  │     ├── Check YAML syntax
  │     ├── Check draft/date/tags types
  │     └── Check closing ---
  ├── Missing layout?
  │     └── Add layout or fix page layout field
  ├── Duplicate URL?
  │     ├── Adjust slug/permalink
  │     └── Use continue-on-error to inspect partial output
  ├── Write error?
  │     ├── Check permissions
  │     └── Verify output_dir path
  └── Asset error?
        └── Check static_dir and file permissions
```

---

## Maintenance Notes

- Keep `SiteBuilder` as orchestration, not business logic storage.
- Keep config/output safety tests strong.
- Add tests before changing permalink behavior.
- Add tests before expanding template syntax.
- Preserve HTML escaping by default.
- Keep generated pages in the site model, not ad hoc render logic.
- Keep manifest schema versioned.
- Document any new output artifacts.
- Treat incremental cache invalidation as correctness-sensitive.
- Keep CLI exit codes stable.

---

*Constitution reference: Article 6 (behavior verification), Article 5 (constraints and trade-offs), and Article 8 (verifiable learner work).*

---


# Lessons Learned
## App — Static Site Generator
**Publishing Pipeline Group | Document 5 of 5**

---

## Why This Design Was Chosen

This design was chosen because a static site generator is mostly a pipeline problem. Content starts as Markdown files, then becomes parsed documents, then page models, then a site graph, then rendered HTML, then filesystem output. Trying to collapse those steps into one function would make the tool harder to verify and harder to explain.

The design also reflects a deliberate balance between product usefulness and scope discipline. The app supports real static-site features — front matter, layouts, partials, generated tag pages, generated collection pages, navigation, previous/next links, assets, sitemap, manifest, incremental builds, watch, and local serve — without becoming a full CMS or frontend framework.

---

## What Was Intentionally Omitted

**Full Jinja support:** The project only needs a small layout adapter.

**RSS feeds:** Explicitly out of scope.

**Asset bundling/minification:** Static assets are copied, not transformed.

**Database or admin UI:** Content lives in files.

**Live rebuild server as a separate product:** Watch mode is local tooling only.

**Plugin architecture:** Deferred until core behavior is stable.

**Remote deploy command:** Out of scope.

---

## Biggest Weakness

The biggest weakness is the limited template adapter. It keeps the system understandable and safe, but authors may quickly want loops, includes, macros, nested conditionals, or filters beyond `safe`. The current design is excellent for constrained layouts, but it is not a general template engine.

The second weakness is the watch implementation. Polling is easy to maintain and cross-platform, but it is not as efficient as filesystem event notifications.

The third weakness is incremental build complexity. Once a generator supports partial rebuild behavior, cache correctness becomes a major concern. The project handles fingerprints and stale output pruning, but future features must be careful not to bypass cache invalidation.

---

## Scaling Considerations

**If sites grow larger:**
- track per-page dependency graphs
- avoid re-rendering pages unaffected by content/layout changes
- cache Markdown conversion results
- benchmark discovery and rendering separately

**If templates grow richer:**
- either integrate Jinja2 or build a formal parser
- preserve escaping-by-default behavior
- define exact semantics for loops/includes/macros

**If deployment support is added:**
- add a dry-run deploy plan
- never delete remote files without a manifest comparison
- make output artifact checks explicit

**If plugins are added:**
- define stable hook points per stage
- version plugin interfaces
- isolate plugin failures by stage

---

## What the Next Refactor Would Be

1. **Formalize template parsing** — replace regex conditionals with a small parser if syntax expands.

2. **Add per-page dependency tracking** — improve incremental rebuild precision.

3. **Add JSON manifest schema docs** — document manifest consumers can rely on.

4. **Add optional Jinja adapter** — preserve the current adapter as default/simple mode.

5. **Add RSS generation** — only after defining feed metadata requirements.

---

## What This Project Taught

- **Pipelines need boundaries.** Each stage should have clear input, output, and failure behavior.

- **Filesystem safety matters.** A build tool that cleans directories must defend against destructive paths.

- **Warnings are useful.** Unknown front matter, missing optional directories, and skipped generated pages should not always be fatal.

- **Static sites still need security defaults.** HTML escaping should be the default; raw output should be explicit.

- **Generated pages are real pages.** Tags and collection indexes must participate in URL collision checks, navigation, manifests, and rendering.

- **Manifests make builds observable.** Counts, warnings, errors, output files, and stale removals provide a durable audit trail.

- **Incremental builds are harder than they look.** Hashes, global dependencies, stale output pruning, and manifests all need to work together.

---

*Constitution v2.0 checklist: This document satisfies Article 5 (trade-off documentation), Article 6 (verification), and Article 7 (progressive complexity) for Static Site Generator.*
