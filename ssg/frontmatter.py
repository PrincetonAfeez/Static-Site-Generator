""" Static Site Generator Frontmatter """

from __future__ import annotations

from datetime import date
from typing import Any

import yaml

from .errors import FrontMatterError
from .models import ParsedDocument, SourceFile


SUPPORTED_FIELDS = {
    "title",
    "date",
    "tags",
    "layout",
    "draft",
    "slug",
    "description",
    "author",
}


def parse_document(source: SourceFile) -> ParsedDocument:
    raw_text = source.path.read_text(encoding="utf-8")
    warnings: list[str] = []
    metadata, body = split_frontmatter(raw_text, source, warnings)
    return ParsedDocument(
        source=source,
        metadata=metadata,
        body_markdown=body,
        raw_text=raw_text,
        warnings=warnings,
    )


def split_frontmatter(
    text: str, source: SourceFile, warnings: list[str] | None = None
) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        raise FrontMatterError(
            "front matter block is missing a closing ---",
            path=source.path,
            line=1,
        )

    metadata_text = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :])
    if text.endswith("\n"):
        body += "\n"
    return parse_yaml_metadata(metadata_text, source, warnings, start_line=2), body


def parse_yaml_metadata(
    text: str,
    source: SourceFile,
    warnings: list[str] | None,
    *,
    start_line: int = 2,
) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {}

    try:
        loaded = yaml.safe_load(stripped)
    except yaml.YAMLError as exc:
        raise FrontMatterError(
            f"invalid YAML front matter: {exc}",
            path=source.path,
            line=start_line,
        ) from exc

    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise FrontMatterError(
            "front matter must be a YAML mapping",
            path=source.path,
            line=start_line,
        )

    metadata: dict[str, Any] = {}
    for raw_key, raw_value in loaded.items():
        if not isinstance(raw_key, str):
            raise FrontMatterError(
                "front matter keys must be strings",
                path=source.path,
                line=start_line,
            )
        key = raw_key.strip().lower()
        if not key:
            raise FrontMatterError(
                "metadata key cannot be empty",
                path=source.path,
                line=start_line,
            )
        if key not in SUPPORTED_FIELDS and warnings is not None:
            warnings.append(f"[frontmatter] {source.path}: unknown front matter field '{key}'")
        metadata[key] = normalize_value(key, raw_value, source, start_line)
    return metadata


def normalize_value(key: str, value: Any, source: SourceFile, line: int) -> Any:
    if key == "draft":
        return normalize_draft(value, source, line)

    if key == "tags":
        return normalize_tags(value, source, line)

    if key == "date":
        return normalize_date(value, source, line)

    if value is None:
        return ""
    if isinstance(value, bool | int | float):
        return str(value)
    if not isinstance(value, str):
        raise FrontMatterError(
            f"unsupported value type for {key}: {type(value).__name__}",
            path=source.path,
            line=line,
        )
    return value


def normalize_draft(value: Any, source: SourceFile, line: int) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    raise FrontMatterError(
        f'invalid boolean for draft: "{value}"',
        path=source.path,
        line=line,
    )


def normalize_tags(value: Any, source: SourceFile, line: int) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_normalize_tag(tag) for tag in value.split(",") if _normalize_tag(tag)]
    if isinstance(value, list):
        tags: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise FrontMatterError(
                    "tag entries must be strings",
                    path=source.path,
                    line=line,
                )
            normalized = _normalize_tag(item)
            if normalized:
                tags.append(normalized)
        return tags
    raise FrontMatterError(
        "tags must be a comma-separated string or YAML list",
        path=source.path,
        line=line,
    )


def normalize_date(value: Any, source: SourceFile, line: int) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise FrontMatterError(
                f'invalid date: "{value}"',
                path=source.path,
                line=line,
            ) from exc
        return value
    raise FrontMatterError(
        f'invalid date: "{value}"',
        path=source.path,
        line=line,
    )


def _normalize_tag(tag: str) -> str:
    return tag.strip().lower()


# Backward-compatible helpers retained for tests that import private escape helpers.
def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        quote = value[0]
        inner = value[1:-1]
        if quote == '"':
            return _unescape_double_quoted(inner)
        return _unescape_single_quoted(inner)
    return value


def _unescape_single_quoted(value: str) -> str:
    chars: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\":
            chars.append(char)
            index += 1
            continue
        if index + 1 >= len(value):
            chars.append("\\")
            index += 1
            continue
        escape = value[index + 1]
        if escape == "'":
            chars.append("'")
        elif escape == "\\":
            chars.append("\\")
        else:
            chars.append("\\")
            chars.append(escape)
        index += 2
    return "".join(chars)


def _unescape_double_quoted(value: str) -> str:
    chars: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\":
            chars.append(char)
            index += 1
            continue
        if index + 1 >= len(value):
            chars.append("\\")
            index += 1
            continue
        escape = value[index + 1]
        if escape == '"':
            chars.append('"')
        elif escape == "\\":
            chars.append("\\")
        else:
            chars.append("\\")
            chars.append(escape)
        index += 2
    return "".join(chars)
