from __future__ import annotations

import pytest

from ssg.config import load_config
from ssg.errors import ConfigError


def test_config_loads_defaults(site_root):
    config = load_config(site_root / "site.toml")

    assert config.title == "Test Site"
    assert config.content_dir == site_root / "content"
    assert config.output_dir == site_root / "dist"
    assert config.clean_output is True


def test_config_rejects_unsafe_output_dir(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace('output_dir = "dist"', 'output_dir = "."'),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_config_rejects_malformed_toml(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text('title = \nbase_url = "oops"', encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_config_rejects_missing_content_dir(site_root):
    import shutil

    shutil.rmtree(site_root / "content")

    with pytest.raises(ConfigError):
        load_config(site_root / "site.toml")


def test_config_rejects_permalink_missing_slug(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'permalink = "/{path}/{slug}/"', 'permalink = "/{path}/post/"'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_config_reads_scaffold_post_collections(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + '\n[scaffold]\npost_collections = ["blog", "notes"]\n',
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.post_collections == ("blog", "notes")


def test_config_override_does_not_mutate_original(site_root):
    config = load_config(site_root / "site.toml", include_drafts=True)

    assert config.include_drafts is True


def test_config_accepts_flat_slug_permalink(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'permalink = "/{path}/{slug}/"', 'permalink = "/{slug}/"'
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.permalink == "/{slug}/"


def test_config_rejects_unknown_permalink_placeholder(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'permalink = "/{path}/{slug}/"', 'permalink = "/{year}/{slug}/"'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_config_string_list_error_includes_path(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\n[scaffold]\npost_collections = 42\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as error:
        load_config(config_path)

    assert error.value.path is not None
    assert str(config_path) == str(error.value.path)


def test_config_reads_assets_dir(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "[build]", 'assets_dir = "static-files"\n\n[build]'
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.assets_dir == "static-files"


def test_config_rejects_traversal_assets_dir(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "[build]", 'assets_dir = "../escape"\n\n[build]'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as error:
        load_config(config_path)

    assert "assets_dir" in str(error.value)


def test_config_rejects_absolute_assets_dir(site_root, tmp_path):
    abs_path = str(tmp_path / "elsewhere").replace("\\", "/")
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "[build]", f'assets_dir = "{abs_path}"\n\n[build]'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as error:
        load_config(config_path)

    assert "assets_dir" in str(error.value)


def test_config_rejects_non_dict_build_section(site_root):
    config_path = site_root / "site.toml"
    # Replace the [build] table with a scalar to trigger _section's type check.
    text = config_path.read_text(encoding="utf-8")
    text = text.replace("[build]\ndrafts = false\nclean = true", 'build = "oops"')
    config_path.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigError) as error:
        load_config(config_path)

    assert "[build]" in str(error.value)


def test_site_config_replace_creates_new_instance(site_root):
    import dataclasses as dc

    config = load_config(site_root / "site.toml")
    updated = dc.replace(config, include_drafts=True)

    assert updated.include_drafts is True
    assert config.include_drafts is False
    assert updated is not config


def test_string_tuple_error_includes_field_name(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\n[scaffold]\npost_collections = 42\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as error:
        load_config(config_path)

    assert "post_collections" in str(error.value)
