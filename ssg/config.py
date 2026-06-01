from __future__ import annotations

import dataclasses
import re
import tomllib
from pathlib import Path
from typing import Any

from .errors import ConfigError
from .models import SiteConfig


PERMALINK_PLACEHOLDER = re.compile(r"\{([^}]+)\}")
ALLOWED_PERMALINK_TOKENS = {"path", "slug"}


def load_config(
    config_path: str | Path = "site.toml",
    *,
    include_drafts: bool | None = None,
    clean_output: bool | None = None,
) -> SiteConfig:
    path = Path(config_path)
    if not path.exists():
        raise ConfigError("config file not found", path=path)
    if not path.is_file():
        raise ConfigError("config path is not a file", path=path)

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(str(exc), path=path) from exc

    root_dir = path.parent.resolve()
    build_data = _section(data, "build", path)
    scaffold_data = _section(data, "scaffold", path)

    config = SiteConfig(
        root_dir=root_dir,
        title=str(data.get("title", "My Static Site")),
        base_url=str(data.get("base_url", "")),
        content_dir=_resolve(root_dir, data.get("content_dir", "content")),
        layout_dir=_resolve(root_dir, data.get("layout_dir", "layouts")),
        partial_dir=_resolve(root_dir, data.get("partial_dir", "partials")),
        static_dir=_resolve(root_dir, data.get("static_dir", "static")),
        output_dir=_resolve(root_dir, data.get("output_dir", "dist")),
        default_layout=str(data.get("default_layout", "page.html")),
        permalink=str(data.get("permalink", "/{path}/{slug}/")),
        include_drafts=bool(build_data.get("drafts", False)),
        clean_output=bool(build_data.get("clean", True)),
        post_collections=_string_tuple(
            scaffold_data.get("post_collections", ["blog"]),
            field_name="post_collections",
            source_path=path,
        ),
        assets_dir=str(data.get("assets_dir", "assets")),
    )

    if include_drafts is not None:
        config = dataclasses.replace(config, include_drafts=include_drafts)
    if clean_output is not None:
        config = dataclasses.replace(config, clean_output=clean_output)

    validate_config(config)
    return config


def validate_config(config: SiteConfig) -> None:
    if not config.title.strip():
        raise ConfigError("site title cannot be empty")
    if not config.default_layout.strip():
        raise ConfigError("default_layout cannot be empty")
    if not config.permalink.startswith("/"):
        raise ConfigError("permalink must start with /")
    if "{slug}" not in config.permalink:
        raise ConfigError("permalink must include {slug}")
    unknown = {
        token
        for token in PERMALINK_PLACEHOLDER.findall(config.permalink)
        if token not in ALLOWED_PERMALINK_TOKENS
    }
    if unknown:
        raise ConfigError(
            f"permalink contains unknown placeholder(s): {', '.join(sorted(unknown))}"
        )
    if not config.assets_dir.strip():
        raise ConfigError("assets_dir cannot be empty")
    assets_path = Path(config.assets_dir)
    if assets_path.is_absolute():
        raise ConfigError("assets_dir must be relative")
    if ".." in assets_path.parts:
        raise ConfigError("assets_dir cannot contain '..'")
    if not config.content_dir.exists():
        raise ConfigError("content directory not found", path=config.content_dir)
    if not config.content_dir.is_dir():
        raise ConfigError("content path is not a directory", path=config.content_dir)
    if not config.layout_dir.exists():
        raise ConfigError("layout directory not found", path=config.layout_dir)
    if not config.layout_dir.is_dir():
        raise ConfigError("layout path is not a directory", path=config.layout_dir)
    ensure_safe_output_dir(config)


def ensure_safe_output_dir(config: SiteConfig) -> None:
    root = config.root_dir.resolve()
    output = config.output_dir.resolve()

    if not _is_relative_to(output, root):
        raise ConfigError("output_dir must be inside the site root", path=output)
    if output == root:
        raise ConfigError("output_dir cannot be the site root", path=output)

    protected = [
        config.content_dir.resolve(),
        config.layout_dir.resolve(),
        config.static_dir.resolve(),
        config.partial_dir.resolve(),
        Path.home().resolve(),
    ]
    for protected_path in protected:
        if output == protected_path:
            raise ConfigError("output_dir points at a protected directory", path=output)

    anchor = Path(output.anchor).resolve() if output.anchor else output
    if output == anchor:
        raise ConfigError("output_dir cannot be a drive or filesystem root", path=output)


def _resolve(root_dir: Path, value: Any) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path.resolve()
    return (root_dir / path).resolve()


def _section(data: dict[str, Any], key: str, source_path: Path) -> dict[str, Any]:
    value = data.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"[{key}] must be a table", path=source_path)
    return value


def _string_tuple(value: Any, *, field_name: str, source_path: Path) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    raise ConfigError(f"{field_name}: expected a string or list of strings", path=source_path)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
