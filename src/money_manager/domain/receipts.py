"""Receipts: a photo or PDF attached to a transaction, kept in the database."""

from dataclasses import dataclass
from datetime import datetime

MAX_RECEIPT_BYTES = 10 * 1024 * 1024
MAX_RECEIPTS_PER_TRANSACTION = 10
RECEIPT_TYPES = {  # extension -> media type (images and PDF only)
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
    ".gif": "image/gif", ".bmp": "image/bmp", ".pdf": "application/pdf",
}
# The first bytes of each kind of file, so a renamed file is not accepted.
SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",), "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/gif": (b"GIF87a", b"GIF89a"), "image/bmp": (b"BM",),
    "application/pdf": (b"%PDF-",), "image/webp": (b"RIFF",),
}


@dataclass(frozen=True, slots=True)
class Receipt:
    id: int
    transaction_id: int
    file_name: str
    media_type: str
    size: int
    added_at: datetime


def matches_signature(media_type: str, content: bytes) -> bool:
    if media_type == "image/webp":
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    return any(content.startswith(prefix) for prefix in SIGNATURES.get(media_type, ()))
