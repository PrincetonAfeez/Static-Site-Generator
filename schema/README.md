# Static Site Generator Schema

This folder contains lightweight JSON Schema contracts for the Static Site Generator project.

## Files

- `site.schema.json` — validates the global site configuration.
- `page.schema.json` — validates individual content pages/posts.
- `asset.schema.json` — validates static assets such as images, CSS, JavaScript, fonts, and documents.
- `build-manifest.schema.json` — validates the generated build manifest after a site build.

## Suggested usage

Keep project configuration and generated metadata consistent by validating JSON/YAML inputs against these schemas during development or before each build.

Example folder placement:

```text
schema/
  README.md
  site.schema.json
  page.schema.json
  asset.schema.json
  build-manifest.schema.json
```

These schemas intentionally stay simple so they can grow with the project.
