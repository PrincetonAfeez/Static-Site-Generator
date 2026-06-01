.PHONY: install check test lint format typecheck coverage example

install:
	pip install -r requirements.txt -r requirements-dev.txt -e .

lint:
	ruff check ssg tests

format:
	ruff format ssg tests

format-check:
	ruff format --check ssg tests

typecheck:
	mypy ssg

coverage:
	pytest --cov=ssg --cov-report=term-missing --cov-fail-under=90

test:
	pytest -v

check: lint format-check typecheck coverage

example:
	python -m ssg build --config example_site/site.toml
