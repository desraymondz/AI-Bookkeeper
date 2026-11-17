"""The only outbound Telegram path. See planning/03-tech-stack.md#5-langgraph-layout."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Supplier, User, UserRole, UserStatus
from bookkeeper.telegram.app import BotLike

if TYPE_CHECKING:
    from bookkeeper.telegram.router import Sender

log = logging.getLogger(__name__)


async def boss_chat_id(session: AsyncSession) -> int | None:
    return await session.scalar(
        select(User.telegram_user_id).where(
            User.role == UserRole.BOSS,
            User.status == UserStatus.ACTIVE,
            User.telegram_user_id.is_not(None),
        )
    )


async def to_boss(
    session: AsyncSession, bot: BotLike, text: str, *, reply_markup: Any = None
) -> Any | None:
    chat_id = await boss_chat_id(session)
    if chat_id is None:
        return None
    return await bot.send_message(chat_id, text, reply_markup=reply_markup)


async def to_supplier(
    session: AsyncSession,
    bot: BotLike,
    supplier_id: int,
    text: str,
    *,
    reply_markup: Any = None,
) -> int:
    chat_ids = (
        await session.scalars(
            select(User.telegram_user_id)
            .join(Supplier, User.supplier_id == Supplier.id)
            .where(
                User.supplier_id == supplier_id,
                User.role == UserRole.SUPPLIER,
                User.status == UserStatus.ACTIVE,
                User.telegram_user_id.is_not(None),
                Supplier.active.is_(True),
            )
        )
    ).all()
    targets = [chat_id for chat_id in chat_ids if chat_id is not None]
    for chat_id in targets:
        await bot.send_message(chat_id, text, reply_markup=reply_markup)
    if not targets:
        log.warning("no active linked user for supplier %s", supplier_id)
    return len(targets)


async def to_sender(bot: BotLike, sender: Sender, text: str, *, reply_markup: Any = None) -> Any:
    return await bot.send_message(sender.telegram_user_id, text, reply_markup=reply_markup)


async def edit_for_sender(
    bot: BotLike, sender: Sender, message_id: int, text: str, *, reply_markup: Any = None
) -> Any:
    return await bot.edit_message_text(
        text, chat_id=sender.telegram_user_id, message_id=message_id, reply_markup=reply_markup
    )


async def answer_callback(bot: BotLike, callback_query_id: str, text: str | None = None) -> Any:
    return await bot.answer_callback_query(callback_query_id, text=text)
