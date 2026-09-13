from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class PageText:
    page: Optional[int]
    text: str
    section: Optional[str] = None


@dataclass
class ParseResult:
    pages: list[PageText]
    page_count: int
    warnings: list[str] = field(default_factory=list)


class Parser(Protocol):
    def can_handle(self, source_type: str) -> bool: ...
    def parse(self, path: str) -> ParseResult: ...
