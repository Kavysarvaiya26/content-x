from pathlib import Path

import httpx
import trafilatura

from app.core.security import validate_public_url
from app.services.parsers.base import PageText, ParseResult


class UrlParser:
    def can_handle(self, source_type: str) -> bool:
        return source_type == "url"

    def parse(self, path: str) -> ParseResult:
        url = Path(path).read_text(encoding="utf-8").strip() if Path(path).exists() else path
        validate_public_url(url)
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            response = client.get(url, headers={"User-Agent": "TransformAI/1.0"})
            response.raise_for_status()
            if len(response.content) > 2_000_000:
                raise ValueError("Remote page exceeds size limit")
            html = response.text
        extracted = trafilatura.extract(html, include_comments=False) or ""
        if not extracted.strip():
            raise ValueError("URL contained no extractable text")
        return ParseResult(pages=[PageText(page=1, text=extracted, section=url)], page_count=1)
