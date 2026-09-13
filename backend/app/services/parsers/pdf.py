import fitz

from app.services.parsers.base import PageText, ParseResult


class PdfParser:
    def can_handle(self, source_type: str) -> bool:
        return source_type == "pdf"

    def parse(self, path: str) -> ParseResult:
        warnings: list[str] = []
        pages: list[PageText] = []
        doc = fitz.open(path)
        try:
            page_count = doc.page_count
            for i, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                if not text.strip():
                    warnings.append(f"ocr_required:page_{i}")
                    continue
                pages.append(PageText(page=i, text=text, section=f"Page {i}"))
        finally:
            doc.close()
        if not pages:
            raise ValueError("PDF contained no extractable text")
        return ParseResult(pages=pages, page_count=page_count, warnings=warnings)
