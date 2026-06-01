# ADR 0002: Markdown Library Behind an Adapter

## Decision

Use Python-Markdown behind `MarkdownConverter`.

## Reason

The project is about build-pipeline architecture, not Markdown parsing.

## Trade-off

The app has one external runtime dependency.
