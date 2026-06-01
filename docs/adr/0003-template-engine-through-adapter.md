# ADR 0003: Template Engine Through an Adapter

## Decision

Render layouts through `TemplateRenderer`.

## Reason

The SSG should depend on a renderer boundary, not a specific template
implementation.

## Trade-off

The fallback adapter only supports simple variable interpolation.
