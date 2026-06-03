# ADR 0003: Template Engine Through an Adapter 

## Status

Accepted

## Context

Layouts must combine site metadata, page fields, and partial HTML. A full template
language (Jinja2, Django templates) would add dependency weight and learning
surface area beyond the course focus.

The project reuses concepts from a minimal template engine (variable interpolation,
basic conditionals) but keeps rendering behind an explicit adapter.

## Decision

Implement `TemplateRenderer` in `ssg/template_adapter.py` with:

- `{{ expression }}` — HTML-escaped by default
- `{{ expression | safe }}` — trusted raw HTML
- `{% if expression %}…{% endif %}` — single-level conditionals only

Layouts and partials are rendered only through this adapter and `renderer.py`.

## Alternatives considered

| Alternative | Why not chosen |
|-------------|----------------|
| Jinja2 | Powerful but heavy; blurs SSG vs template-engine coursework. |
| String `.format()` only | No conditionals; awkward for optional prev/next links. |
| Embedded Django | Conflicts with [ADR 0004](0004-no-web-layer.md). |

## Consequences

**Positive**

- Zero additional template dependencies.
- Predictable, testable behaviour with explicit limitations documented in README.
- Clear boundary for future replacement with Jinja2 or another engine.

**Negative**

- No loops, includes, macros, or nested conditionals.
- Authors must use generated listing pages or pre-built HTML for index content.
- Filter support limited to `| safe` only.

## References

- `ssg/template_adapter.py`, `ssg/renderer.py`
- `tests/test_template_adapter.py`
