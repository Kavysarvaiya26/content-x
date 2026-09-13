from pathlib import Path

from app.services.parsers.base import PageText, ParseResult


class TxtParser:
    def can_handle(self, source_type: str) -> bool:
        return source_type in {"txt", "text"}

    def parse(self, path: str) -> ParseResult:
        raw = Path(path).read_bytes()
        text = _decode(raw)
        if not text.strip():
            raise ValueError("Text file is empty")
        return ParseResult(pages=[PageText(page=1, text=text, section="Document")], page_count=1)


def _decode(raw: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")
