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

Optional **local preview** is limited to `ssg serve` — a thin wrapper around
`http.server` for development.

## Alternatives considered

| Alternative | Why not chosen |
|-------------|----------------|
| Django admin for content | Out of scope; shifts focus to web app development. |
| Live rebuild on save | Requires watch process; deferred to future work. |
| Headless CMS integration | External service; not required for core pipeline demonstration. |

## Consequences

**Positive**

- Single deployment artifact: files in `dist/`.
- No runtime server requirement in production.
- Clear separation from web-framework coursework.

**Negative**

- No in-browser editing; authors use Markdown files and `ssg new`.
- Preview requires manual rebuild before refresh (unless browser hard-refreshes static files).

## References

- README “Scope” section
- `ssg/cli.py` — `serve` command
