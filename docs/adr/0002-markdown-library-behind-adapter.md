# ADR 0002: Markdown Library Behind an Adapter 

## Status

Accepted

## Context

Markdown parsing is a solved problem with mature libraries (Python-Markdown,
mistune, etc.). This project’s learning goals focus on **build-pipeline
architecture** — discovery, models, rendering, and output — not on implementing
parsers or HTML serializers.

Direct imports of a Markdown library throughout the codebase would couple the
pipeline to one API and complicate testing.

## Decision

Isolate Python-Markdown behind `MarkdownConverter` in `ssg/markdown_adapter.py`.
The rest of the pipeline receives HTML strings from `SiteBuilder._collect_source_pages`
and never imports `markdown` directly.

Default extensions: `["extra"]` (tables, fenced code, etc.).

## Alternatives considered

| Alternative | Why not chosen |
|-------------|----------------|
| mistune | Python-Markdown is widely used and sufficient for course scope. |
| Inline `markdown()` calls in builder | Violates single-responsibility; harder to mock in tests. |
| Custom Markdown subset | Reinvents a wheel unrelated to SSG architecture learning goals. |

## Consequences

**Positive**

- One runtime dependency with a stable boundary.
- Tests can monkeypatch `MarkdownConverter.convert` without patching third-party code.
- Future swap to another library requires changes in one module.

**Negative**

- Behaviour is tied to Python-Markdown’s extension model and HTML output.
- Import errors surface at converter construction time if `Markdown` is not installed.

## References

- `ssg/markdown_adapter.py`
- `tests/test_markdown_adapter.py`
