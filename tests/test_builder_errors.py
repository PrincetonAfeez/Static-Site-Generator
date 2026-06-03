""" Test Builder Errors """

from __future__ import annotations

import pytest

from ssg.builder import SiteBuilder
from ssg.errors import MarkdownConversionError


def test_markdown_error_carries_source_path(site_root, monkeypatch):
    from ssg import markdown_adapter

    def boom(text, extensions=None):
        raise RuntimeError("simulated markdown crash")

    monkeypatch.setattr(markdown_adapter._markdown, "markdown", boom)

    with pytest.raises(MarkdownConversionError) as error:
        SiteBuilder(site_root / "site.toml").build()

    assert error.value.path is not None
    # First markdown file by sort order is about.md.
    assert "about.md" in str(error.value.path)
