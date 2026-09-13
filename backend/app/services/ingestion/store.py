from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.security import sanitize_filename, sniff_source_type
from app.db.models import Source, SourceChunk
from app.services.parsers import get_parser
from app.services.parsers.base import ParseResult

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 120


def save_upload(filename: str, data: bytes, content_type: str) -> Source:
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise ValueError("file_too_large")
    if not data:
        raise ValueError("empty_file")
    source_type = sniff_source_type(filename, data[:16])
    safe = sanitize_filename(filename)
    
    source = Source(
        id=str(uuid4()),
        filename=filename,
        safe_filename=safe,
        source_type=source_type,
        content_type=content_type or "application/octet-stream",
        size_bytes=len(data),
    )
    dest_dir = settings.upload_dir / source.id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / safe
    dest.write_bytes(data)
    source.storage_path = str(dest)
    return source


def persist_chunks(source: Source, parse: ParseResult) -> list[SourceChunk]:
    chunks: list[SourceChunk] = []
    idx = 1
    total_chars = 0
    for page in parse.pages:
        text = page.text.strip()
        total_chars += len(text)
        start = 0
        while start < len(text):
            end = min(len(text), start + CHUNK_SIZE)
            piece = text[start:end]
            chunks.append(
                SourceChunk(
                    source_id=source.id,
                    chunk_id=f"c{idx}",
                    page=page.page,
                    section=page.section,
                    start_char=start,
                    end_char=end,
                    text=piece,
                )
            )
            idx += 1
            if end >= len(text):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
    source.page_count = parse.page_count
    source.char_count = total_chars
    source.extract_preview = (parse.pages[0].text[:800] if parse.pages else "")[:800]
    return chunks


def extract_source(source: Source) -> tuple[list[SourceChunk], list[str]]:
    if source.source_type == "url":
        parser = get_parser("url")
        result = parser.parse(source.origin_url or source.storage_path or "")
    else:
        path = source.storage_path
        if not path or not Path(path).exists():
            raise ValueError("Source file is missing")
        parser = get_parser(source.source_type)
        result = parser.parse(path)
    chunks = persist_chunks(source, result)
    return chunks, result.warnings
