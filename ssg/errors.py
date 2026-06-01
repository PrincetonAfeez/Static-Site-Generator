from __future__ import annotations

from pathlib import Path


class SSGError(Exception):
    stage = "ssg"

    def __init__(
        self,
        message: str,
        *,
        path: str | Path | None = None,
        line: int | None = None,
        stage: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.path = Path(path) if path is not None else None
        self.line = line
        if stage is not None:
            self.stage = stage

    def __str__(self) -> str:
        location = ""
        if self.path is not None:
            location = str(self.path)
            if self.line is not None:
                location = f"{location}:{self.line}"
            location = f" {location}:"
        return f"[{self.stage}]{location} {self.message}"


class CLIError(Exception):
    stage = "cli"

    def __init__(
        self,
        message: str,
        *,
        path: str | Path | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.path = Path(path) if path is not None else None

    def __str__(self) -> str:
        location = ""
        if self.path is not None:
            location = f" {self.path}:"
        return f"[{self.stage}]{location} {self.message}"


class ConfigError(SSGError):
    stage = "config"


class DiscoveryError(SSGError):
    stage = "discovery"


class FrontMatterError(SSGError):
    stage = "frontmatter"


class MarkdownConversionError(SSGError):
    stage = "markdown"


class PageBuildError(SSGError):
    stage = "page-build"


class SiteModelError(SSGError):
    stage = "site-model"


class TemplateRenderError(SSGError):
    stage = "render"


class MissingLayoutError(TemplateRenderError):
    pass


class OutputWriteError(SSGError):
    stage = "write"


class AssetCopyError(SSGError):
    stage = "assets"


class BuildError(SSGError):
    stage = "build"
