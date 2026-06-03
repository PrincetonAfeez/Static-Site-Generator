# ADR 0006: Incremental Builds and Watch Mode 

## Status

Accepted (supplements ADR 0001)

## Context

ADR 0001 chose full rebuilds for simplicity. Portfolio review identified incremental
builds, watch mode, and live reload as high-value extensions that remain tractable
at modest site scale without a dependency graph engine.

## Decision

Add **opt-in incremental mode** (`--incremental` or `[build] incremental = true`):

- Skip cleaning `dist/` (same as `--no-clean`).
- Track SHA-256 fingerprints of config, layouts, partials, static files, and content.
- Store fingerprints and last output file list in `.ssg-cache.json`.
- After each build, prune output files present in the previous manifest but absent from the current build.
- Skip copying static assets when the static tree hash is unchanged.

Add **`ssg watch`** with polling-based file watching, debounced rebuilds, optional
background `serve`, and browser live reload via `/__ssg_reload`.

Add **`sitemap.xml`** generation (default on) using absolute URLs from `base_url`.

Upgrade front matter parsing to **YAML** via PyYAML.

**RSS feeds remain out of scope.**

## Consequences

**Positive**

- Faster iteration during local development.
- Stale HTML removed after deleted content without a full clean.
- Sitemap and YAML front matter improve real-world usability.

**Negative**

- Incremental mode still re-renders all pages (no per-page cache); global layout changes rebuild everything.
- Watch mode uses polling, not native OS file events.
- PyYAML adds a runtime dependency and increases front matter parser complexity.

## References

- [ADR 0001](0001-full-rebuild-over-incremental.md)
- `ssg/cache.py`, `ssg/watch.py`, `ssg/sitemap.py`
