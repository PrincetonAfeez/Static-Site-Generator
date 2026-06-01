# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `site.nav_html` and `page.canonical_url` template context fields.
- Iterative partial pre-rendering for nested partial references.
- Explicit rejection of nested `{% if %}` blocks.
- Collection directory slug-collision warnings.
- `requirements-dev.txt` with pinned pytest, mypy, and ruff.
- Ruff lint step in CI.

### Fixed

- Front matter double-quoted escape sequences (`\"`, `\\`) parse correctly.
- Tag and collection generators share a single reserved-URL registry.
- Generated pages validated for layout existence before render.
- `--continue-on-error` survives `SiteModelError` by falling back to source pages.
- CLI summary reports `Build finished with errors.` when pages failed.
- `pages_failed` manifest counter tracks distinct failed pages.
- Example header uses generated `site.nav_html`; layouts emit canonical URLs.
- Setuptools license metadata uses SPDX `MIT` format.

### Changed

- README pipeline, template, and development sections updated.
- List/dict template values render as escaped repr strings.

## [0.1.0]

### Added

- Library core (`SiteBuilder`) and CLI (`build`, `clean`, `new`, `serve`).
- Markdown adapter behind `MarkdownConverter` (Python-Markdown).
- Front matter parser with line-aware errors and unknown-field warnings.
- Configurable permalink template — `{path}` optional, `{slug}` required,
  unknown placeholders rejected at load time.
- Tag and collection grouping with auto-generated index pages; URL collisions
  with content pages are skipped with a warning rather than failing the build.
- Navigation tree with URLs attached to intermediate collection nodes.
- Previous / next links within the dated subset of each collection.
- Partial loader at the SSG layer; duplicate stems raise, missing references
  warn, filter syntax (`{{ site.partials.X | safe }}`) is recognised.
- Build manifest with warnings, errors, per-stage counters, POSIX-formatted
  output file list, and a `pages_failed` counter.
- Safety-checked output cleaning and `--output-dir` override re-validated
  against the site root.
- `--continue-on-error` mode that survives parse, convert, page-build,
  render, and write failures.
- Configurable `assets_dir` mirroring `static/` into `dist/<assets_dir>/`.
- `--version` flag, `__version__` attribute, and `py.typed` marker.
- Listing HTML escapes page titles and URLs.

[0.1.0]: https://github.com/princ/static-site-generator/releases/tag/v0.1.0
