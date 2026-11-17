"""Fixtures for Telegram webhook tests. See planning/decisions.md#D-031."""

from collections.abc import Iterator
from typing import cast

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from tests.support.factories import seeded_chart, supplier
from tests.support.fakes import RecordingBot

from bookkeeper.db.models import Supplier, User, UserRole, UserStatus
from bookkeeper.telegram import handlers
from bookkeeper.telegram.app import drain
from bookkeeper.telegram.router import Handler

BOSS_ID = 1001
SUPPLIER_ID = 2002
DEACTIVATED_ID = 3003
STRANGER_ID = 4004
WEBHOOK_PATH = "/telegram/webhook"
SECRET = "test_webhook_secret"


def app_of(client: httpx.AsyncClient) -> FastAPI:
    transport = getattr(client, "_transport")  # noqa: B009
    return cast(FastAPI, transport.app)


@pytest.fixture
def tg_app(client: httpx.AsyncClient, bot: RecordingBot) -> FastAPI:
    app = app_of(client)
    app.state.bot = bot
    return app


@pytest.fixture
def registry() -> Iterator[list[Handler]]:
    saved = list(handlers.HANDLERS)
    handlers.HANDLERS.clear()
    try:
        yield handlers.HANDLERS
    finally:
        handlers.HANDLERS[:] = saved


async def post_update(
    client: httpx.AsyncClient,
    app: FastAPI,
    update: dict[str, object],
    *,
    secret: str | None = SECRET,
) -> httpx.Response:
    headers = {"X-Telegram-Bot-Api-Secret-Token": secret} if secret is not None else {}
    res = await client.post(WEBHOOK_PATH, json=update, headers=headers)
    await drain(app)
    return res


@pytest.fixture
async def people(db_session: AsyncSession) -> dict[str, Supplier | None]:
    await seeded_chart(db_session)
    active = await supplier(db_session, "Ocean Fresh", "5000")
    inactive = await supplier(db_session, "Old Dairy", "5000", active=False)
    db_session.add_all(
        [
            User(telegram_user_id=BOSS_ID, role=UserRole.BOSS, status=UserStatus.ACTIVE),
            User(
                telegram_user_id=SUPPLIER_ID,
                role=UserRole.SUPPLIER,
                supplier_id=active.id,
                status=UserStatus.ACTIVE,
            ),
            User(
                telegram_user_id=DEACTIVATED_ID,
                role=UserRole.SUPPLIER,
                supplier_id=inactive.id,
                status=UserStatus.DEACTIVATED,
            ),
        ]
    )
    await db_session.flush()
    return {"active": active, "inactive": inactive}
