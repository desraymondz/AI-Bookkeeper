"""POST /telegram/webhook. See planning/01-prd.md (F-009)."""

import hmac
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update

from bookkeeper.db.models import TelegramUpdate
from bookkeeper.telegram.app import spawn
from bookkeeper.telegram.router import process_update
from bookkeeper.web_api import get_db

router = APIRouter()

SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


def _secret_ok(provided: str | None, expected: str) -> bool:
    return provided is not None and hmac.compare_digest(provided.encode(), expected.encode())


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    secret: Annotated[str | None, Header(alias=SECRET_HEADER)] = None,
) -> dict[str, bool]:
    if not _secret_ok(secret, request.app.state.settings.telegram_webhook_secret):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        payload: Any = json.loads(await request.body())
        update = Update.de_json(payload, bot=None) if isinstance(payload, dict) else None
    except ValueError, TypeError, KeyError:
        update = None
    if update is None:
        return {"ok": True}

    inserted = await session.scalar(
        insert(TelegramUpdate)
        .values(update_id=update.update_id)
        .on_conflict_do_nothing()
        .returning(TelegramUpdate.update_id)
    )
    await session.commit()
    if inserted is not None:
        spawn(request.app, process_update(request.app, update))
    return {"ok": True}
