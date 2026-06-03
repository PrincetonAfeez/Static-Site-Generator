""" Test Config Extended """

from __future__ import annotations

import pytest

from ssg.config import load_config, validate_config
from ssg.errors import ConfigError


def test_config_rejects_missing_file(site_root):
    with pytest.raises(ConfigError, match="not found"):
        load_config(site_root / "missing.toml")


def test_config_rejects_directory_as_config_path(site_root):
    with pytest.raises(ConfigError, match="not a file"):
        load_config(site_root / "content")


def test_config_rejects_empty_title(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace('title = "Test Site"', 'title = "   "'),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="title cannot be empty"):
        load_config(config_path)


def test_config_rejects_empty_default_layout(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'default_layout = "page.html"', 'default_layout = "  "'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="default_layout"):
        load_config(config_path)


def test_config_rejects_permalink_without_leading_slash(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'permalink = "/{path}/{slug}/"', 'permalink = "no-leading/"'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="must start with /"):
        load_config(config_path)


def test_config_rejects_empty_assets_dir(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("[build]", 'assets_dir = "   "\n\n[build]'),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="assets_dir"):
        load_config(config_path)


def test_config_rejects_content_path_not_directory(site_root):
    config_path = site_root / "site.toml"
    file_content = site_root / "content-file"
    file_content.write_text("x", encoding="utf-8")
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'content_dir = "content"', f'content_dir = "{file_content.name}"'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="not a directory"):
        load_config(config_path)


def test_config_rejects_layout_path_not_directory(site_root):
    config_path = site_root / "site.toml"
    layout_file = site_root / "layouts-file"
    layout_file.write_text("x", encoding="utf-8")
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'layout_dir = "layouts"', f'layout_dir = "{layout_file.name}"'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="not a directory"):
        load_config(config_path)


def test_config_rejects_output_equal_to_content(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'output_dir = "dist"', 'output_dir = "content"'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="protected directory"):
        load_config(config_path)


def test_config_rejects_non_dict_build_section(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "[build]\ndrafts = false\nclean = true", "build = 42"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="must be a table"):
        load_config(config_path)


def test_config_scaffold_single_string_collection(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + '\n[scaffold]\npost_collections = "blog"\n',
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.post_collections == ("blog",)


def test_config_absolute_path_resolution(site_root, tmp_path):
    config_path = site_root / "site.toml"
    abs_content = tmp_path / "abs-content"
    abs_content.mkdir()
    (abs_content / "index.md").write_text("# Home\n", encoding="utf-8")
    config_path.write_text(
        "\n".join(
            [
                'title = "Abs"',
                f'content_dir = "{abs_content.as_posix()}"',
                'layout_dir = "layouts"',
                'output_dir = "dist"',
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.content_dir == abs_content.resolve()


def test_validate_config_direct(site_root):
    config = load_config(site_root / "site.toml")

    validate_config(config)
