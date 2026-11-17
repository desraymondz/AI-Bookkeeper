"""PDF text layer read in code, no LLM. See planning/decisions.md#D-034."""

import asyncio
import io

from pypdf import PdfReader


def _read(data: bytes) -> str | None:
    try:
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception:
        return None
    return text or None


async def pdf_text(data: bytes, mime: str) -> str | None:
    if mime != "application/pdf":
        return None
    return await asyncio.to_thread(_read, data)
