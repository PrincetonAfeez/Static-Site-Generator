# ADR 0005: Generated Pages Before Final Render

## Decision

Add generated pages before final URL validation and rendering.

## Reason

Generated pages should use the same model, layout, and collision checks as
content pages.

## Trade-off

The pipeline does not stream render output as files are discovered.
