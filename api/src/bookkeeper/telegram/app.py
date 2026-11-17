"""Bot provider, background task tracking and session access for the webhook.

See planning/03-tech-stack.md#3.2-runtime-libraries (python-telegram-bot row).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Coroutine
from contextlib import asynccontextmanager
from typing import Any, Protocol, cast

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot

from bookkeeper.config import Settings
from bookkeeper.web_api import get_db


class BotLike(Protocol):
    async def send_message(self, chat_id: int, text: str, reply_markup: Any = None) -> Any: ...

    async def edit_message_text(
        self,
        text: str,
        chat_id: int | None = None,
        message_id: int | None = None,
        reply_markup: Any = None,
    ) -> Any: ...

    async def answer_callback_query(
        self, callback_query_id: str, text: str | None = None
    ) -> Any: ...


def get_bot(app: FastAPI) -> BotLike:
    existing: BotLike | None = getattr(app.state, "bot", None)
    if existing is not None:
        return existing
    settings: Settings = app.state.settings
    created = cast(BotLike, Bot(settings.telegram_bot_token))
    app.state.bot = created
    return created


def _tasks(app: FastAPI) -> set[asyncio.Task[None]]:
    tasks: set[asyncio.Task[None]] | None = getattr(app.state, "telegram_tasks", None)
    if tasks is None:
        tasks = set()
        app.state.telegram_tasks = tasks
    return tasks


def spawn(app: FastAPI, work: Coroutine[Any, Any, None]) -> None:
    tasks = _tasks(app)
    task = asyncio.get_running_loop().create_task(work)
    tasks.add(task)
    task.add_done_callback(tasks.discard)


async def drain(app: FastAPI) -> None:
    while pending := list(_tasks(app)):
        await asyncio.gather(*pending, return_exceptions=True)


@asynccontextmanager
async def open_session(app: FastAPI) -> AsyncIterator[AsyncSession]:
    override = app.dependency_overrides.get(get_db)
    if override is not None:
        gen: AsyncIterator[AsyncSession] = override()
        session = await anext(gen)
        try:
            yield session
        finally:
            await gen.aclose()  # type: ignore[attr-defined]
        return
    async with app.state.sessionmaker() as session:
        yield session
