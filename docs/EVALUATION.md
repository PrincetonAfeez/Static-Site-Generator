# Project Evaluation

Self-assessment and traceability for academic / portfolio review. This project
implements the scope in [spec/static_site_generator_improved_full_scope.txt](spec/static_site_generator_improved_full_scope.txt).

## Self-assessment rubric

| Dimension | Score (1–10) | Evidence |
|-----------|:------------:|----------|
| Requirements & scope | 9 | Spec traceability table below; explicit “out of scope” in README |
| Architecture & design | 9 | [ARCHITECTURE.md](ARCHITECTURE.md), 5 ADRs, adapter boundaries |
| Implementation quality | 9 | Typed Python, staged pipeline, structured errors, 4 audit cycles |
| Testing & CI | 10 | 285 tests, ≥97% coverage on `ssg/`, mypy strict on `ssg/` + typed tests |
| Documentation | 9 | README, CHANGELOG, CONTRIBUTING, SECURITY, this document |
| Reproducibility | 9 | Pinned deps, `make check`, GitHub Actions |
| Security & safety | 8 | Path containment, HTML escaping model in [SECURITY.md](SECURITY.md) |
| CLI / UX | 9 | Full CLI, watch + live reload, incremental builds, exit codes |
| Portfolio presentation | 8 | Example site, tagged releases, MIT license (pending public push) |
| Academic reflection | 9 | Audit history, ADRs (including 0006), limitations, trade-offs |

**Overall:** Portfolio-ready static site generator demonstrating pipeline architecture,
defensive filesystem handling, and iterative quality improvement.

## Spec traceability

| Requirement | Implementation | Tests / demo |
|-------------|----------------|--------------|
| Library + CLI | `SiteBuilder`, `ssg.cli` | `test_cli.py`, `test_pipeline_integration.py` |
| Markdown → HTML | `markdown_adapter.py` | `test_markdown_adapter.py` |
| Front matter parser | `frontmatter.py` | `test_frontmatter.py` |
| Configurable permalink | `config.py`, `page_builder.derive_url` | `test_config.py`, `test_page_builder.py` |
| Tag pages | `site_model.generate_tag_pages` | `test_site_model.py`, `example_site` |
| Collection pages | `site_model.generate_collection_pages` | `test_site_model.py`, `example_site` |
| Navigation tree + URLs | `site_model.build_nav_tree` | `test_site_model.py`, `test_renderer.py` |
| Previous / next links | `assign_previous_next` | `test_site_model.py` |
| Partials | `renderer.load_partials` | `test_renderer.py` |
| Template adapter | `template_adapter.py` | `test_template_adapter.py` |
| Static assets | `assets.py` | `test_writer_assets.py` |
| Build manifest | `manifest.py`, `builder._build_manifest` | `test_pipeline_integration.py` |
| Safe output clean | `writer.clean_output_dir` | `test_config.py`, `test_writer_assets.py` |
| Continue on error | `SiteBuilder.continue_on_error` | `test_pipeline_integration.py`, `test_cli.py` |
| Draft filtering | `builder._assemble_site_model` | `test_pipeline_integration.py` |
| Scaffold new content | `scaffold.py` | `test_cli.py`, `test_scaffold.py` |
| Local serve | `cli.serve`, `cli.watch` | `test_cli.py`, `test_watch.py` |
| Incremental build | `cache.py`, `SiteBuilder(incremental=True)` | `test_cache.py`, `test_new_features.py` |
| Sitemap | `sitemap.py` | `test_sitemap.py` |
| YAML front matter | `frontmatter.py` (PyYAML) | `test_frontmatter.py` |

## Audit history

Four structured code audits were performed during development:

1. **Audit #1** — 28 issues (tag collisions, template escaping, manifest, CI, tests).
2. **Audit #2** — 23 issues (front matter escapes, nested if, continue-on-error, nav).
3. **Audit #3** — 16 issues (double-escape, manifest counts, recursive nav, dedupe).
4. **Audit #4** — 18 issues (bool truthiness, pages_failed semantics, manifest ordering).

Each round produced a finite fix list; fixes were implemented and verified with pytest,
mypy, and ruff.

## Known limitations (accepted)

- **Incremental re-renders all pages** — cache skips clean/static copy and prunes stale files; no per-page render cache ([ADR 0006](adr/0006-incremental-watch-sitemap-yaml.md)).
- **Minimal templates** — no loops, includes, or nested `{% if %}`; only `\| safe` filter.
- **Partial namespace** — keyed by filename stem, not subdirectory path.
- **No RSS or asset bundling** — RSS deliberately out of scope; no minification pipeline.
- **Watch uses polling** — no native OS file watcher; dev-only live reload.
- **Serve is dev-only** — no production server.

## Future work (if extending beyond course scope)

1. Per-page render cache with dependency tracking (layout → all pages).
2. RSS feed generation from dated collection pages.
3. Native file watcher (e.g. watchdog) instead of polling.

## Demo script (≈5 minutes)

1. `pip install -r requirements-dev.txt -e .`
2. `python -m ssg build --config example_site/site.toml --verbose`
3. Open `example_site/dist/.ssg-manifest.json` — show counters and POSIX paths.
4. Open `example_site/dist/tags/python/index.html` — generated tag listing.
5. `python -m ssg build --config example_site/site.toml --continue-on-error` with a bad layout file — show manifest errors.
6. `python -m ssg watch --config example_site/site.toml` — edit a post and show live reload.

## Course alignment

This project demonstrates:

- **Staged pipeline architecture** with clear module boundaries.
- **Adapter pattern** for Markdown and templates.
- **Defensive I/O** (output directory containment, slug validation).
- **Test-driven quality** with integration and unit tests.
- **Architecture decision records** documenting trade-offs.

See [ARCHITECTURE.md](ARCHITECTURE.md) and [SECURITY.md](SECURITY.md) for technical depth.
