# ADR 0004: No Web Layer 

## Status

Accepted

## Context

Static site generators produce **flat files** suitable for any static host (GitHub
Pages, S3, nginx). Some course stacks combine content management with Django,
HTMX, or admin UIs. This project is scoped as a **library + CLI** file transformer.

## Decision

Do **not** implement:

- Django or any WSGI/ASGI application
- HTMX or client-side dynamic UI
- Database-backed content or user accounts
- Browser-based authoring or admin panels

Optional **local preview** is limited to CLI commands such as `ssg serve` and
`ssg watch` (see ADR 0006) — thin development helpers, not a production web layer.

## Alternatives considered

| Alternative | Why not chosen |
|-------------|----------------|
| Django admin for content | Out of scope; shifts focus to web app development. |
| Live rebuild on save | Requires watch process; deferred to future work. |
| Headless CMS integration | External service; not required for core pipeline demonstration. |

Historical note: At the time of ADR 0004, live rebuild on save was deferred. ADR 0006
later introduced local-only `ssg watch` with polling, debounced rebuilds, optional
preview serving, and browser live reload. This does not change the no-web-layer
decision because watch mode remains a local development CLI feature, not a
production web application.

## Consequences

**Positive**

- Single deployment artifact: files in `dist/`.
- No runtime server requirement in production.
- Clear separation from web-framework coursework.

**Negative**

- No in-browser editing; authors use Markdown files and `ssg new`.
- Without `ssg watch`, preview requires manual rebuild before refresh.

## References

- README “Scope” section
- `ssg/cli.py` — `serve` and `watch` commands
- [ADR 0006](0006-incremental-watch-sitemap-yaml.md) — local watch mode and live reload
