from __future__ import annotations

from datetime import date
from typing import Any

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

    metadata_lines = lines[1:closing_index]
    body = "\n".join(lines[closing_index + 1 :])
    if text.endswith("\n"):
        body += "\n"
    return parse_metadata(metadata_lines, source, warnings), body


def parse_metadata(
    lines: list[str], source: SourceFile, warnings: list[str] | None = None
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for offset, line in enumerate(lines, start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            raise FrontMatterError(
                "expected key: value",
                path=source.path,
                line=offset,
            )

        key, raw_value = line.split(":", 1)
        key = key.strip().lower()
        value = raw_value.strip()
        if not key:
            raise FrontMatterError("metadata key cannot be empty", path=source.path, line=offset)
        if key not in SUPPORTED_FIELDS and warnings is not None:
            warnings.append(
                f"[frontmatter] {source.path}:{offset}: unknown front matter field '{key}'"
            )
        metadata[key] = parse_value(key, value, source, offset)

    return metadata


def parse_value(key: str, value: str, source: SourceFile, line: int) -> Any:
    value = _unquote(value.strip())
    if key == "draft":
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        raise FrontMatterError(
            f'invalid boolean for draft: "{value}"',
            path=source.path,
            line=line,
        )

    if key == "tags":
        if not value:
            return []
        return [_normalize_tag(tag) for tag in value.split(",") if _normalize_tag(tag)]

    if key == "date" and value:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise FrontMatterError(
                f'invalid date: "{value}"',
                path=source.path,
                line=line,
            ) from exc
        return value

    return value


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


def _normalize_tag(tag: str) -> str:
    return tag.strip().lower()
