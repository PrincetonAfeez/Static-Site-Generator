""" Static Site Generator Template Adapter """

from __future__ import annotations

import html
import re
from typing import Any

from .errors import TemplateRenderError


VARIABLE_PATTERN = re.compile(r"{{\s*(.*?)\s*}}")
IF_OPEN_PATTERN = re.compile(r"{%\s*if\s+", re.IGNORECASE)
IF_BLOCK_PATTERN = re.compile(
    r"{%\s*if\s+(.*?)\s*%}(.*?){%\s*endif\s*%}",
    re.DOTALL | re.IGNORECASE,
)


class TemplateRenderer:
    """Small adapter fallback for App 52-style variable interpolation."""

    def render(self, template_text: str, context: dict[str, Any]) -> str:
        text = _render_conditionals(template_text, context)

        def replace(match: re.Match[str]) -> str:
            raw = match.group(1)
            parts = raw.split("|", 1)
            expression = parts[0].strip()
            use_safe = len(parts) > 1 and parts[1].strip().lower() == "safe"
            value = resolve_expression(expression, context)
            if value is None:
                return ""
            text_value = format_template_value(value, use_safe=use_safe)
            if use_safe:
                return text_value
            return html.escape(text_value)

        return VARIABLE_PATTERN.sub(replace, text)


def resolve_expression(expression: str, context: dict[str, Any]) -> Any:
    current: Any = context
    for part in expression.split("."):
        part = part.strip()
        if not part:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return None
    return current


def format_template_value(value: Any, *, use_safe: bool = False) -> str:
    if use_safe:
        return str(value)
    if isinstance(value, (list, dict, tuple, set)):
        return repr(value)
    return str(value)


def _render_conditionals(template_text: str, context: dict[str, Any]) -> str:
    text = template_text
    while True:
        match = IF_BLOCK_PATTERN.search(text)
        if match is None:
            break
        body = match.group(2)
        if IF_OPEN_PATTERN.search(body):
            raise TemplateRenderError("nested {% if %} blocks are not supported")
        expression = match.group(1).strip()
        value = resolve_expression(expression, context)
        replacement = body if _is_truthy(value) else ""
        text = text[: match.start()] + replacement + text[match.end() :]
    return text


def _is_truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return bool(value)
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True
