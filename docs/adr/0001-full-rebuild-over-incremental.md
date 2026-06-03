# ADR 0001: Full Rebuild Over Incremental Builds 

## Status

Accepted

## Context

Static site generators can either rebuild the entire output tree on every run or
track changes and rebuild only affected pages. Incremental systems need cache
invalidation, dependency graphs (e.g. layout change → all pages), and careful
handling of deleted source files.

This project is an academic exercise in pipeline architecture at modest scale
(tens of pages, not tens of thousands). Correctness and clarity matter more than
build latency.

## Decision

Use a **clean full rebuild** for every `ssg build` invocation when `clean = true`
(the default). The pipeline discovers all content, regenerates all derived pages,
renders all pages, and writes a fresh `dist/` tree.

## Alternatives considered

| Alternative | Why not chosen |
|-------------|----------------|
| Incremental builds with file mtimes | Adds cache invalidation complexity disproportionate to site size. |
| Watch mode with incremental updates | Out of scope; requires long-running process and debouncing. |
| Content-addressable cache | Useful at scale; not required to demonstrate core SSG concepts. |

## Consequences

**Positive**

- Deleted or renamed source files cannot leave stale HTML in output after a clean build.
- Layout or template changes automatically apply to every page on the next build.
- Easier to reason about and test — no hidden cache state.

**Negative**

- Every build processes the entire site; not suitable for very large sites without extension.
- `--no-clean` preserves unrelated files in `output_dir` but still re-renders all pages.

## References

- [ARCHITECTURE.md](../ARCHITECTURE.md) — pipeline stages
- `ssg/writer.py` — `clean_output_dir`
