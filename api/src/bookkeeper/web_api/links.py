"""See planning/01-prd.md (F-006.1, F-006.2, F-007.2)."""

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper import linking
from bookkeeper.db.models import LinkPurpose, Supplier, User, UserRole, UserStatus
from bookkeeper.web_api import get_db

router = APIRouter(prefix="/api/links", tags=["links"])

Db = Annotated[AsyncSession, Depends(get_db)]


class LinkOut(BaseModel):
    token: str
    url: str
    expires_at: dt.datetime


class BossLinkState(BaseModel):
    connected: bool
    username: str | None
    display_name: str | None
    linked_at: dt.datetime | None


def _out(request: Request, token: str, expires_at: dt.datetime) -> LinkOut:
    bot = request.app.state.settings.telegram_bot_username
    return LinkOut(token=token, url=linking.deep_link(bot, token), expires_at=expires_at)


@router.get("/boss", response_model=BossLinkState)
async def read_boss_link(session: Db) -> BossLinkState:
    boss = await session.scalar(
        select(User).where(
            User.role == UserRole.BOSS,
            User.status == UserStatus.ACTIVE,
            User.telegram_user_id.is_not(None),
        )
    )
    if boss is None:
        return BossLinkState(connected=False, username=None, display_name=None, linked_at=None)
    return BossLinkState(
        connected=True,
        username=boss.username,
        display_name=boss.display_name,
        linked_at=boss.linked_at,
    )


@router.post("/boss", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def create_boss_link(request: Request, session: Db) -> LinkOut:
    token, row = await linking.create_token(session, LinkPurpose.BOSS, now=linking.utcnow())
    await session.commit()
    return _out(request, token, row.expires_at)


@router.post(
    "/suppliers/{supplier_id}", response_model=LinkOut, status_code=status.HTTP_201_CREATED
)
async def create_supplier_link(supplier_id: int, request: Request, session: Db) -> LinkOut:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    if not supplier.active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Supplier is deactivated")
    token, row = await linking.create_token(
        session, LinkPurpose.SUPPLIER, supplier_id=supplier.id, now=linking.utcnow()
    )
    await session.commit()
    return _out(request, token, row.expires_at)
