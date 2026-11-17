"""See planning/01-prd.md#f-011 and #g-6. Boss-only file download."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Document
from bookkeeper.storage import resolve_path
from bookkeeper.web_api import get_db

router = APIRouter(prefix="/api/documents", tags=["documents"])

Db = Annotated[AsyncSession, Depends(get_db)]


async def _serve(
    db: AsyncSession, request: Request, document_id: int, preview: bool
) -> FileResponse:
    document = await db.get(Document, document_id)
    relative = (
        document.preview_path if document and preview else document.path if document else None
    )
    if document is None or relative is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    path = resolve_path(request.app.state.settings.storage_dir, relative)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Document not found.")
    media_type = "image/jpeg" if preview else document.mime
    return FileResponse(path, media_type=media_type)


@router.get("/{document_id}/file")
async def get_document_file(db: Db, request: Request, document_id: int) -> FileResponse:
    return await _serve(db, request, document_id, preview=False)


@router.get("/{document_id}/preview")
async def get_document_preview(db: Db, request: Request, document_id: int) -> FileResponse:
    return await _serve(db, request, document_id, preview=True)
