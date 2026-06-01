from __future__ import annotations

import argparse
import logging
import sys
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from . import __version__
from .builder import SiteBuilder
from .config import load_config
from .errors import CLIError, SSGError
from .scaffold import scaffold_content
from .writer import remove_output_dir


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            _configure_logging(verbose=args.verbose, quiet=args.quiet)
            result = SiteBuilder(
                args.config,
                include_drafts=args.drafts,
                clean_output=args.clean,
                output_dir=args.output_dir,
                continue_on_error=args.continue_on_error,
            ).build()
            if not args.quiet:
                print_build_summary(result)
            if result.manifest.pages_failed > 0:
                return 1
            return 0

        if args.command == "clean":
            config = load_config(args.config)
            remove_output_dir(config)
            print(f"Cleaned {config.output_dir}")
            return 0

        if args.command == "new":
            config = load_config(args.config)
            path = scaffold_content(config, args.path, args.title)
            print(f"Created {path}")
            return 0

        if args.command == "serve":
            return serve(args.config, args.host, args.port)

        raise CLIError("unknown command")
    except CLIError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except SSGError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI wrapper
        print(f"[internal] {exc}", file=sys.stderr)
        return 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ssg")
    parser.add_argument("--version", action="version", version=f"ssg {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build the static site")
    build.add_argument("--config", default="site.toml")
    build.add_argument(
        "--drafts",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="include or exclude draft pages (overrides site.toml)",
    )
    build.add_argument(
        "--clean",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="clean the output directory before building (overrides site.toml)",
    )
    build.add_argument("--verbose", action="store_true")
    build.add_argument("--quiet", action="store_true", help="suppress non-error output")
    build.add_argument(
        "--continue-on-error",
        action="store_true",
        default=False,
        help="skip pages that fail to build instead of aborting",
    )
    build.add_argument("--output-dir", default=None, help="override output_dir from site.toml")

    clean = subparsers.add_parser("clean", help="remove the output directory")
    clean.add_argument("--config", default="site.toml")

    new = subparsers.add_parser("new", help="create a new content file")
    new.add_argument("path")
    new.add_argument("--title")
    new.add_argument("--config", default="site.toml")

    serve_parser = subparsers.add_parser("serve", help="serve dist/ locally")
    serve_parser.add_argument("--config", default="site.toml")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    return parser


def _configure_logging(*, verbose: bool, quiet: bool) -> None:
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    # Reset handlers so repeated CLI invocations in the same process pick up
    # the new level (e.g. tests calling main() multiple times).
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    logging.basicConfig(level=level, format="%(message)s")


def print_build_summary(result) -> None:
    manifest = result.manifest
    if manifest.pages_failed > 0:
        print("Build finished with errors.")
    else:
        print("Built site successfully.")
    print(f"  pages discovered: {manifest.pages_discovered}")
    print(f"  pages rendered: {manifest.pages_rendered}")
    print(f"  generated pages: {manifest.generated_pages}")
    print(f"  drafts skipped: {manifest.drafts_skipped}")
    print(f"  pages failed: {manifest.pages_failed}")
    print(f"  assets copied: {manifest.assets_copied}")
    print(f"  output: {result.config.output_dir}")
    print(f"  elapsed: {manifest.elapsed_seconds:.2f}s")
    if manifest.warnings:
        print(f"  warnings: {len(manifest.warnings)}")
        for warning in manifest.warnings:
            print(f"    - {warning}")
    if manifest.errors:
        print(f"  errors: {len(manifest.errors)}")
        for error in manifest.errors:
            print(f"    - {error}")


def serve(config_path: str, host: str, port: int) -> int:
    config = load_config(config_path)
    if not config.output_dir.exists():
        raise CLIError("output directory does not exist; run build first", path=config.output_dir)

    handler_factory = partial(SimpleHTTPRequestHandler, directory=str(config.output_dir))
    try:
        httpd = ThreadingHTTPServer((host, port), handler_factory)
    except OSError as exc:
        raise CLIError(f"could not bind {host}:{port} — {exc}") from exc

    print(f"Serving {config.output_dir} at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server")
    finally:
        httpd.server_close()
    return 0
