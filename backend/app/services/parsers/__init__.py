from app.services.parsers.docx import DocxParser
from app.services.parsers.pdf import PdfParser
from app.services.parsers.txt import TxtParser
from app.services.parsers.url import UrlParser

PARSERS = [PdfParser(), TxtParser(), DocxParser(), UrlParser()]


def get_parser(source_type: str):
    for parser in PARSERS:
        if parser.can_handle(source_type):
            return parser
    raise ValueError(f"No parser for source type {source_type}")
