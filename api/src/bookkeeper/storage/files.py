"""See planning/01-prd.md#f-011 and planning/03-tech-stack.md section 9."""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path

import pillow_heif
from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Document, DocumentKind

MAX_BYTES = 20 * 1024 * 1024

_HEIC_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"}
_EXTENSIONS = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
}


@dataclass(frozen=True, slots=True)
class StoredDocument:
    document: Document
    duplicate: bool


def detect_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[4:8] == b"ftyp" and data[8:12] in _HEIC_BRANDS:
        return "image/heic"
    return None


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "supplier"


def resolve_path(storage_dir: Path, relative: str) -> Path | None:
    root = storage_dir.resolve()
    target = (root / relative).resolve()
    return target if target.is_relative_to(root) else None


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _heic_preview(data: bytes) -> bytes:
    pillow_heif.register_heif_opener()
    with Image.open(io.BytesIO(data)) as image:
        rotated = ImageOps.exif_transpose(image).convert("RGB")
    out = io.BytesIO()
    rotated.save(out, format="JPEG", quality=85)
    return out.getvalue()


async def store_document(
    session: AsyncSession,
    storage_dir: Path,
    *,
    data: bytes,
    mime: str,
    supplier_name: str,
    sender_user_id: int | None,
    received_at: dt.datetime,
) -> StoredDocument:
    digest = hashlib.sha256(data).hexdigest()
    existing = await session.scalar(select(Document).where(Document.sha256 == digest))
    if existing is not None:
        return StoredDocument(existing, duplicate=True)

    relative = (
        f"invoices/{received_at:%Y}/{received_at:%m}/{slugify(supplier_name)}/"
        f"{digest}.{_EXTENSIONS[mime]}"
    )
    _write(storage_dir / relative, data)
    preview_relative: str | None = None
    if mime == "image/heic":
        preview_relative = f"previews/{digest}.jpg"
        _write(storage_dir / preview_relative, _heic_preview(data))

    document = Document(
        path=relative,
        preview_path=preview_relative,
        sha256=digest,
        mime=mime,
        size=len(data),
        sender_user_id=sender_user_id,
        received_at=received_at,
        kind=DocumentKind.INVOICE,
    )
    session.add(document)
    await session.flush()
    return StoredDocument(document, duplicate=False)
