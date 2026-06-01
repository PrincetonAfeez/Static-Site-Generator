from __future__ import annotations

import pytest

from ssg.cli import main


def test_cli_build_and_clean(site_root, capsys):
    assert main(["build", "--config", str(site_root / "site.toml")]) == 0
    assert (site_root / "dist" / "index.html").exists()

    assert main(["clean", "--config", str(site_root / "site.toml")]) == 0
    assert not (site_root / "dist").exists()


def test_cli_new_scaffolds_quoted_title(site_root):
    assert (
        main(
            [
                "new",
                "blog/my-post",
                "--title",
                'My Post: "Special" Edition',
                "--config",
                str(site_root / "site.toml"),
            ]
        )
        == 0
    )

    created = site_root / "content" / "blog" / "my-post.md"
    content = created.read_text(encoding="utf-8")
    assert 'title: "My Post: \\"Special\\" Edition"' in content


def test_cli_new_scaffolds_content_file(site_root):
    assert (
        main(
            [
                "new",
                "blog/new-post",
                "--title",
                "New Post",
                "--config",
                str(site_root / "site.toml"),
            ]
        )
        == 0
    )

    created = site_root / "content" / "blog" / "new-post.md"
    assert created.exists()
    content = created.read_text(encoding="utf-8")
    assert "title: New Post" in content
    assert "description: " in content
    assert "author: " in content
    assert "layout: post.html" in content


def test_cli_new_uses_page_layout_for_non_post_collection(site_root):
    assert (
        main(["new", "notes/idea", "--title", "Idea", "--config", str(site_root / "site.toml")])
        == 0
    )

    created = site_root / "content" / "notes" / "idea.md"
    assert "layout: page.html" in created.read_text(encoding="utf-8")


def test_cli_build_no_clean_preserves_other_files(site_root):
    sentinel = site_root / "dist" / "sentinel.txt"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("keep", encoding="utf-8")

    assert (
        main(
            [
                "build",
                "--config",
                str(site_root / "site.toml"),
                "--no-clean",
            ]
        )
        == 0
    )

    assert sentinel.exists()


def test_cli_build_output_dir_override(site_root):
    target = site_root / "build" / "preview"

    assert (
        main(
            [
                "build",
                "--config",
                str(site_root / "site.toml"),
                "--output-dir",
                str(target),
            ]
        )
        == 0
    )

    assert (target / "index.html").exists()


def test_cli_build_quiet_suppresses_summary(site_root, capsys):
    assert main(["build", "--config", str(site_root / "site.toml"), "--quiet"]) == 0

    captured = capsys.readouterr()
    assert "Built site successfully" not in captured.out


def test_cli_build_continue_on_error(site_root, capsys):
    bad = site_root / "content" / "broken.md"
    bad.write_text("---\ntitle: Broken\ndraft: maybe\n---\n", encoding="utf-8")

    assert (
        main(
            [
                "build",
                "--config",
                str(site_root / "site.toml"),
                "--continue-on-error",
            ]
        )
        == 1
    )

    captured = capsys.readouterr()
    assert "Build finished with errors." in captured.out

    # The good pages should still be rendered.
    assert (site_root / "dist" / "index.html").exists()


def test_cli_build_drafts_negation(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("drafts = false", "drafts = true"),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "build",
                "--config",
                str(config_path),
                "--no-drafts",
            ]
        )
        == 0
    )

    assert not (site_root / "dist" / "blog" / "draft" / "index.html").exists()


def test_cli_serve_errors_when_output_missing(site_root):
    assert main(["serve", "--config", str(site_root / "site.toml")]) == 2


def test_cli_serve_returns_zero_when_server_starts(site_root, monkeypatch):
    from ssg.builder import SiteBuilder
    import ssg.cli as cli_module

    SiteBuilder(site_root / "site.toml").build()

    class FakeServer:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def serve_forever(self) -> None:
            pass

        def server_close(self) -> None:
            pass

    monkeypatch.setattr(cli_module, "ThreadingHTTPServer", FakeServer)

    assert cli_module.serve(str(site_root / "site.toml"), "127.0.0.1", 8765) == 0


def test_cli_build_explicit_clean_overrides_config(site_root):
    config_path = site_root / "site.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("clean = true", "clean = false"),
        encoding="utf-8",
    )
    sentinel = site_root / "dist" / "sentinel.txt"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("doomed", encoding="utf-8")

    assert main(["build", "--config", str(config_path), "--clean"]) == 0

    assert not sentinel.exists()


def test_cli_build_output_dir_outside_root_fails(site_root, tmp_path):
    target = tmp_path / "elsewhere" / "dist"

    code = main(
        [
            "build",
            "--config",
            str(site_root / "site.toml"),
            "--output-dir",
            str(target),
        ]
    )

    assert code == 1


def test_cli_build_quiet_suppresses_warning_output(site_root, capsys):
    (site_root / "content" / "weird.md").write_text(
        "---\ntitle: Weird\nweird_field: yes\ndraft: false\n---\n# Weird\n",
        encoding="utf-8",
    )

    assert main(["build", "--config", str(site_root / "site.toml"), "--quiet"]) == 0

    captured = capsys.readouterr()
    assert "weird_field" not in captured.out
    assert "warnings:" not in captured.out


def test_cli_version_flag(capsys):
    from ssg import __version__

    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_cli_build_no_clean_with_output_dir(site_root):
    target = site_root / "build" / "preview"
    target.mkdir(parents=True, exist_ok=True)
    sentinel = target / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")

    assert (
        main(
            [
                "build",
                "--config",
                str(site_root / "site.toml"),
                "--output-dir",
                str(target),
                "--no-clean",
            ]
        )
        == 0
    )

    assert (target / "index.html").exists()
    assert sentinel.exists()


def test_cli_build_verbose_prints_stage_logs(site_root, capsys):
    assert main(["build", "--config", str(site_root / "site.toml"), "--verbose"]) == 0

    captured = capsys.readouterr()
    assert "[build] discover" in captured.err


def test_cli_build_internal_error_returns_exit_code_three(site_root, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("unexpected")

    monkeypatch.setattr("ssg.cli.SiteBuilder", boom)

    assert main(["build", "--config", str(site_root / "site.toml")]) == 3
