""" Test Errors """

from __future__ import annotations

from pathlib import Path

import pytest

from ssg.errors import (
    AssetCopyError,
    CLIError,
    ConfigError,
    DiscoveryError,
    FrontMatterError,
    MarkdownConversionError,
    MissingLayoutError,
    OutputWriteError,
    PageBuildError,
    SiteModelError,
    SSGError,
    TemplateRenderError,
)


def test_ssg_error_with_path_and_line():
    error = FrontMatterError("bad value", path=Path("content/x.md"), line=4)

    text = str(error)
    assert "[frontmatter]" in text
    assert "content" in text
    assert "x.md:4" in text
    assert "bad value" in text


def test_ssg_error_with_stage_override():
    error = SSGError("custom", stage="custom-stage")

    assert error.stage == "custom-stage"
    assert "[custom-stage]" in str(error)


def test_cli_error_with_path():
    error = CLIError("missing file", path=Path("dist"))

    assert "[cli]" in str(error)
    assert "dist" in str(error)


@pytest.mark.parametrize(
    "cls",
    [
        ConfigError,
        DiscoveryError,
        MarkdownConversionError,
        PageBuildError,
        TemplateRenderError,
        MissingLayoutError,
        OutputWriteError,
        AssetCopyError,
    ],
)
def test_error_stages(cls):
    error = cls("message", path="file.md")
    assert error.stage in str(error)
    assert "message" in str(error)


def test_site_model_error_conflicting_urls():
    error = SiteModelError(
        "duplicate URL /about/",
        path="/about/",
        conflicting_urls=frozenset({"/about/", "/about/"}),
    )

    assert error.conflicting_urls == frozenset({"/about/"})
