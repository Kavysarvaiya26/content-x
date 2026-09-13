from docx import Document

from app.services.parsers.base import PageText, ParseResult


class DocxParser:
    def can_handle(self, source_type: str) -> bool:
        return source_type == "docx"

    def parse(self, path: str) -> ParseResult:
        doc = Document(path)
        parts: list[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        text = "\n".join(parts)
        if not text.strip():
            raise ValueError("DOCX contained no extractable text")
        return ParseResult(pages=[PageText(page=1, text=text, section="Document")], page_count=1)
