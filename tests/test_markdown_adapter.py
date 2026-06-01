from __future__ import annotations

from ssg.markdown_adapter import MarkdownConverter


def test_markdown_adapter_converts_heading():
    html = MarkdownConverter().convert("# Hello")

    assert "<h1>Hello</h1>" in html
