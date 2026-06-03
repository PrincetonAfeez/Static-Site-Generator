# ADR 0005: Generated Pages Before Final Render 

## Status

Accepted

## Context

Tag and collection index pages are **derived** from content pages — they are not
authored as Markdown files. They must share the same `Page` model, layout validation,
URL collision rules, and rendering path as source pages.

Two orderings are possible: generate listings after rendering content, or generate
page models first and render everything in one pass.

## Decision

**Generate derived pages before building the final `SiteModel` and before rendering:**

1. Build source `Page` objects from Markdown.
2. Filter drafts and validate layouts for source pages.
3. Call `generate_derived_pages()` for tag and collection index pages.
4. Validate layouts for generated pages.
5. Build `SiteModel` from the combined page list (duplicate URL check).
6. Render all pages in `site.pages`.

Generated and source pages share a **single reserved-URL registry** so tag/collection
URLs that collide with content paths are skipped with a warning.

## Alternatives considered

| Alternative | Why not chosen |
|-------------|----------------|
| Render content first, then append listing HTML files | Duplicates rendering logic; generated pages wouldn’t use layouts consistently. |
| Post-process dist/ with separate listing writer | Bypasses template adapter and manifest accounting. |
| Stream render on discover | Harder to compute site-wide nav and prev/next links. |

## Consequences

**Positive**

- One render loop; generated pages appear in `site.pages`, nav, and manifest counts.
- Layout and partial behaviour identical for all pages.
- URL collisions handled uniformly via `SiteModelError` and dedupe fallback.

**Negative**

- Entire site must be modeled before any HTML is written — no streaming output.
- Large sites pay memory cost for holding all pages in memory (acceptable at course scale).

## References

- `ssg/site_model.py` — `generate_derived_pages`
- `ssg/builder.py` — `_assemble_site_model`
- [ARCHITECTURE.md](../ARCHITECTURE.md)
