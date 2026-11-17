"""Boss-only document download. See planning/01-prd.md#f-011."""

import datetime as dt
from pathlib import Path

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Document, DocumentKind


async def test_boss_downloads_file_and_anon_cannot(
    client: httpx.AsyncClient,
    anon_client: httpx.AsyncClient,
    tg_app: FastAPI,
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    tg_app.state.settings = tg_app.state.settings.model_copy(update={"storage_dir": tmp_path})
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 hello")
    doc = Document(
        path="a.pdf",
        sha256="a" * 64,
        mime="application/pdf",
        size=14,
        received_at=dt.datetime.now(dt.UTC),
        kind=DocumentKind.INVOICE,
    )
    escape = Document(
        path="../outside.pdf",
        sha256="b" * 64,
        mime="application/pdf",
        size=1,
        received_at=dt.datetime.now(dt.UTC),
        kind=DocumentKind.INVOICE,
    )
    db_session.add_all([doc, escape])
    await db_session.flush()

    ok = await client.get(f"/api/documents/{doc.id}/file")
    assert ok.status_code == 200
    assert ok.content == b"%PDF-1.4 hello"
    assert (await client.get(f"/api/documents/{doc.id}/preview")).status_code == 404
    assert (await client.get(f"/api/documents/{escape.id}/file")).status_code == 404
    assert (await client.get("/api/documents/9999/file")).status_code == 404
    assert (await anon_client.get(f"/api/documents/{doc.id}/file")).status_code == 401
