# Contributing

Thank you for reviewing this academic portfolio project. It is maintained as a
single-author codebase; this guide helps evaluators and collaborators reproduce
results locally.

## Prerequisites

- Python 3.11 or newer (CI tests 3.11, 3.12, and 3.13 on Ubuntu and Windows)
- Git

## Setup

```powershell
git clone https://github.com/princ/static-site-generator.git
cd static-site-generator
pip install -r requirements.txt -r requirements-dev.txt -e .
```

On Linux/macOS, use the same commands or run `make install`.

## Quality gate

Run the full check suite before submitting changes:

```powershell
.\scripts\check.ps1
```

Or:

```bash
make check
```

This runs, in order:

1. `ruff check ssg tests`
2. `ruff format --check ssg tests`
3. `mypy ssg`
4. `pytest --cov=ssg --cov-fail-under=90`

## Running tests only

```powershell
pytest -v
pytest --cov=ssg --cov-report=term-missing
```

## Project layout

- `ssg/` — library and CLI implementation
- `tests/` — pytest suite
- `example_site/` — runnable demo site (source only; build produces `dist/`)
- `docs/` — architecture, ADRs, spec, evaluation notes

## Commit conventions

Use clear, imperative messages focused on *why*:

- `fix: treat false as false in template if-blocks`
- `docs: expand ADR 0001 with alternatives`
- `test: cover scaffold path traversal rejection`

## Scope

See [README.md](../README.md) “Out of scope” and [docs/EVALUATION.md](EVALUATION.md).
Avoid scope creep (incremental builds, full YAML, theme marketplace) unless the
course spec explicitly requires it.
