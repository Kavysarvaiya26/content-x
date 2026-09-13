import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
BLOCKED_EXTENSIONS = {".exe", ".zip", ".js", ".bat", ".cmd", ".ps1", ".msi", ".scr"}


def sanitize_filename(name: str) -> str:
    base = Path(name or "upload").name
    cleaned = SAFE_FILENAME_RE.sub("_", base).strip("._") or "upload"
    return cleaned[:180]


def sniff_source_type(filename: str, header: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        raise ValueError("File type is not allowed")
    if header.startswith(b"%PDF") or ext == ".pdf":
        if not header.startswith(b"%PDF"):
            raise ValueError("File extension does not match PDF content")
        return "pdf"
    if ext == ".docx":
        if header[:2] != b"PK":
            raise ValueError("File extension does not match DOCX content")
        return "docx"
    if ext == ".txt" or _looks_like_text(header):
        return "txt"
    raise ValueError("Unsupported file type")


def _looks_like_text(header: bytes) -> bool:
    if not header:
        return False
    sample = header[:2048]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        try:
            sample.decode("cp1252")
            return True
        except UnicodeDecodeError:
            return False


def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https URLs are allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("URL host is required")
    if host in {"localhost", "metadata.google.internal"}:
        raise ValueError("URL host is not allowed")
    try:
        infos = socket.getaddrinfo(host, parsed.port or 80, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("URL host could not be resolved") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError("URL resolves to a blocked address")
    return url
