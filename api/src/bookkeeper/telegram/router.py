"""Sender resolution and handler dispatch. See planning/01-prd.md (F-009)."""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update

from bookkeeper.config import Settings
from bookkeeper.db.models import Supplier, TelegramUpdate, User, UserRole, UserStatus
from bookkeeper.telegram import handlers as registry
from bookkeeper.telegram.app import BotLike, get_bot, open_session

log = logging.getLogger(__name__)


class Role(StrEnum):
    BOSS = "boss"
    SUPPLIER = "supplier"
    STRANGER = "stranger"


@dataclass(frozen=True, slots=True)
class Sender:
    role: Role
    telegram_user_id: int
    username: str | None = None
    display_name: str | None = None
    user_id: int | None = None
    supplier_id: int | None = None


@dataclass(slots=True)
class HandlerContext:
    update: Update
    sender: Sender
    session: AsyncSession
    bot: BotLike
    settings: Settings
    app: FastAPI


@dataclass(frozen=True, slots=True)
class Handler:
    name: str
    roles: frozenset[Role]
    matches: Callable[[Update], bool]
    handle: Callable[[HandlerContext], Awaitable[None]]


async def resolve_sender(session: AsyncSession, telegram_user_id: int) -> Sender:
    row = (
        await session.execute(
            select(User, Supplier)
            .outerjoin(Supplier, User.supplier_id == Supplier.id)
            .where(User.telegram_user_id == telegram_user_id)
        )
    ).first()
    if row is not None:
        user, supplier = row
        if user.status == UserStatus.ACTIVE:
            if user.role == UserRole.BOSS:
                return Sender(
                    Role.BOSS, telegram_user_id, user.username, user.display_name, user.id
                )
            if user.role == UserRole.SUPPLIER and supplier is not None and supplier.active:
                return Sender(
                    Role.SUPPLIER,
                    telegram_user_id,
                    user.username,
                    user.display_name,
                    user.id,
                    supplier.id,
                )
    return Sender(Role.STRANGER, telegram_user_id)


def select_handler(update: Update, sender: Sender) -> Handler | None:
    for handler in registry.HANDLERS:
        if sender.role in handler.roles and handler.matches(update):
            return handler
    return None


async def process_update(app: FastAPI, update: Update) -> None:
    user = update.effective_user
    if user is None:
        return
    try:
        async with open_session(app) as session:
            try:
                sender = await resolve_sender(session, user.id)
                if sender.role is Role.STRANGER:
                    sender = Sender(Role.STRANGER, user.id, user.username, user.full_name)
                handler = select_handler(update, sender)
                if handler is not None:
                    ctx = HandlerContext(
                        update, sender, session, get_bot(app), app.state.settings, app
                    )
                    await handler.handle(ctx)
                await session.execute(
                    sa_update(TelegramUpdate)
                    .where(TelegramUpdate.update_id == update.update_id)
                    .values(processed_at=dt.datetime.now(dt.UTC))
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    except Exception:
        log.exception("telegram update %s failed", update.update_id)
