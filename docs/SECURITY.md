# Security

This static site generator is a **local build tool**, not a hosted multi-tenant
service. The security model focuses on safe filesystem access and predictable HTML
output.

## Threat model

| Concern | Mitigation |
|---------|------------|
| Writing outside `output_dir` | `ensure_safe_output_dir()` and `ensure_inside_output()` reject paths that escape the configured output tree. |
| Slug / path traversal in content | `page_builder` rejects slugs containing `..`, `/`, or `\`. |
| Unsafe output directory config | `output_dir` must stay inside the site root and cannot point at `content/`, `layouts/`, `static/`, `partials/`, home, or filesystem roots. |
| XSS in generated HTML | String template values are HTML-escaped by default. Markdown body and partials require explicit `\| safe` in layouts — treat layouts and partials as trusted author input. |
| Secrets in repository | No credentials belong in `site.toml` or content. Use environment-specific config outside git for deployment secrets. |

## HTML escaping

- `{{ page.title }}` — escaped.
- `{{ page.body \| safe }}` — raw HTML from the Markdown converter (trusted author content).
- `{{ site.partials.header \| safe }}` — raw partial output (trusted template author).
- List/dict values render as escaped Python `repr()` strings.

Listing pages generated for tags and collections escape titles and URLs in links.

## Local preview server

`ssg serve` uses Python’s `ThreadingHTTPServer` with `SimpleHTTPRequestHandler`:

- Intended for **local development only**.
- Defaults to `127.0.0.1` — do not expose to untrusted networks without understanding the risk.
- Serves files read-only from `output_dir`; no upload or authentication.

## Reporting issues

For academic / portfolio use, document known limitations in [EVALUATION.md](EVALUATION.md).
For production deployments, review generated HTML and restrict who can edit layouts and content.
