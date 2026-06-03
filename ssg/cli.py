""" Static Site Generator CLI """

from __future__ import annotations

import argparse
import logging
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import IO, Any

from . import __version__
from .builder import SiteBuilder
from .config import load_config
from .errors import CLIError, SSGError
from .models import BuildResult
from .scaffold import scaffold_content
from .watch import ReloadState, run_watch
from .writer import remove_output_dir

LIVE_RELOAD_SNIPPET = """
<script>
(function () {
  var version = null;
  function poll() {
    fetch("/__ssg_reload")
      .then(function (response) { return response.text(); })
      .then(function (value) {
        if (version !== null && version !== value) {
          window.location.reload();
        }
        version = value;
      })
      .catch(function () {});
  }
  setInterval(poll, 500);
  poll();
})();
</script>
"""


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
                incremental=args.incremental,
            ).build()
            if not args.quiet:
                print_build_summary(result)
            if result.manifest.pages_failed > 0 or result.manifest.errors:
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
            return serve(
                args.config,
                args.host,
                args.port,
                live_reload=args.live_reload,
            )

        if args.command == "watch":
            _configure_logging(verbose=args.verbose, quiet=args.quiet)
            return run_watch(
                args.config,
                host=args.host,
                port=args.port,
                serve_site=not args.no_serve,
                live_reload=not args.no_live_reload,
                verbose=args.verbose,
                quiet=args.quiet,
            )

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
    build.add_argument(
        "--incremental",
        action="store_true",
        default=False,
        help="incremental build: skip cleaning dist/ and prune stale outputs",
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
    serve_parser.add_argument(
        "--live-reload",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="inject a live-reload script into served HTML pages",
    )

    watch_parser = subparsers.add_parser(
        "watch",
        help="watch content and rebuild incrementally (optionally serve with live reload)",
    )
    watch_parser.add_argument("--config", default="site.toml")
    watch_parser.add_argument("--host", default="127.0.0.1")
    watch_parser.add_argument("--port", type=int, default=8000)
    watch_parser.add_argument("--verbose", action="store_true")
    watch_parser.add_argument("--quiet", action="store_true")
    watch_parser.add_argument(
        "--no-serve",
        action="store_true",
        help="watch and rebuild without starting the preview server",
    )
    watch_parser.add_argument(
        "--no-live-reload",
        action="store_true",
        help="disable browser live reload when serving during watch",
    )

    return parser


def _configure_logging(*, verbose: bool, quiet: bool) -> None:
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    logging.basicConfig(level=level, format="%(message)s")


def print_build_summary(result: BuildResult) -> None:
    manifest = result.manifest
    if manifest.pages_failed > 0 or manifest.errors:
        print("Build finished with errors.")
    else:
        print("Built site successfully.")
    print(f"  pages discovered: {manifest.pages_discovered}")
    print(f"  pages rendered: {manifest.pages_rendered}")
    print(f"  generated pages: {manifest.generated_pages}")
    print(f"  drafts skipped: {manifest.drafts_skipped}")
    print(f"  pages failed: {manifest.pages_failed}")
    print(f"  assets copied: {manifest.assets_copied}")
    if manifest.incremental:
        print("  incremental: yes")
        print(f"  stale files removed: {manifest.stale_files_removed}")
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


def serve(
    config_path: str | Path,
    host: str,
    port: int,
    *,
    reload_state: ReloadState | None = None,
    live_reload: bool = False,
) -> int:
    config = load_config(config_path)
    if not config.output_dir.exists():
        raise CLIError("output directory does not exist; run build first", path=config.output_dir)

    state = reload_state or (ReloadState() if live_reload else None)
    handler = _build_handler(config.output_dir, state)
    try:
        httpd = ThreadingHTTPServer((host, port), handler)
    except OSError as exc:
        raise CLIError(f"could not bind {host}:{port} — {exc}") from exc

    print(f"Serving {config.output_dir} at http://{host}:{port}")
    if state is not None:
        print("Live reload enabled")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server")
    finally:
        httpd.server_close()
    return 0


def _build_handler(
    directory: Path,
    reload_state: ReloadState | None,
) -> type[SimpleHTTPRequestHandler]:
    class RequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
            super().__init__(*args, directory=str(directory), **kwargs)

        def do_GET(self) -> None:  # noqa: N802
            if reload_state is not None and self.path.split("?", 1)[0] == "/__ssg_reload":
                self._serve_reload_version()
                return
            super().do_GET()

        def _serve_reload_version(self) -> None:
            assert reload_state is not None
            body = str(reload_state.current()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def end_headers(self) -> None:
            if reload_state is not None:
                self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def send_head(self) -> IO[bytes] | None:  # type: ignore[override]
            path = self.translate_path(self.path)
            file_path = Path(path)
            if (
                reload_state is not None
                and file_path.is_file()
                and file_path.suffix.lower() in {".html", ".htm"}
            ):
                self._serve_html_with_reload(file_path)
                return None
            return super().send_head()

        def _serve_html_with_reload(self, file_path: Path) -> None:
            try:
                content = file_path.read_text(encoding="utf-8")
            except OSError:
                self.send_error(404, "File not found")
                return

            if "</body>" in content.lower():
                match = re.search(r"</body>", content, flags=re.IGNORECASE)
                assert match is not None
                index = match.start()
                content = content[:index] + LIVE_RELOAD_SNIPPET + content[index:]
            else:
                content += LIVE_RELOAD_SNIPPET

            encoded = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            if self.command == "GET":
                self.wfile.write(encoded)

    return RequestHandler
