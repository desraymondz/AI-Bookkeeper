"""The only outbound Telegram path. See planning/03-tech-stack.md#5-langgraph-layout."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import User, UserRole, UserStatus
from bookkeeper.telegram.app import BotLike
from bookkeeper.telegram.router import Sender


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
