from __future__ import annotations

from .errors import MarkdownConversionError

try:
    import markdown as _markdown
except ImportError:  # pragma: no cover - exercised only when dependency missing
    _markdown = None  # type: ignore[assignment]


class MarkdownConverter:
    def __init__(self, *, extensions: list[str] | None = None) -> None:
        if _markdown is None:
            raise MarkdownConversionError(
                "python-markdown is not installed; install the 'Markdown' package"
            )
        self.extensions = extensions or ["extra"]

    def convert(self, markdown_text: str) -> str:
        try:
            return _markdown.markdown(markdown_text, extensions=self.extensions)
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise MarkdownConversionError(str(exc)) from exc
