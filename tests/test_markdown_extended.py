""" Test Markdown Extended """

from __future__ import annotations

import pytest

from ssg.discovery import _has_hidden_part
from ssg.errors import MarkdownConversionError
from ssg.markdown_adapter import MarkdownConverter


def test_has_hidden_part_detects_dot_segments():
    from pathlib import Path

    assert _has_hidden_part(Path(".hidden")) is True
    assert _has_hidden_part(Path("ok/.secret")) is True
    assert _has_hidden_part(Path("blog/post")) is False


def test_markdown_converter_missing_library(monkeypatch):
    import ssg.markdown_adapter as adapter

    monkeypatch.setattr(adapter, "_markdown", None)

    with pytest.raises(MarkdownConversionError, match="not installed"):
        adapter.MarkdownConverter()


def test_markdown_converter_wraps_library_errors(monkeypatch):
    import ssg.markdown_adapter as adapter

    def boom(*args, **kwargs):
        raise RuntimeError("markdown internal error")

    monkeypatch.setattr(adapter._markdown, "markdown", boom)

    with pytest.raises(MarkdownConversionError, match="markdown internal error"):
        MarkdownConverter().convert("# Hi")
