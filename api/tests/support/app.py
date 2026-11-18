"""See planning/decisions.md#D-031."""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, cast

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.auth.deps import BossSession, require_boss
from bookkeeper.config import load_settings
from bookkeeper.main import create_app
from bookkeeper.web_api import get_db

if TYPE_CHECKING:
    from tests.support.fakes import RecordingBot

BASE_URL = "http://test"


def build_test_app(db_session: AsyncSession, *, signed_in: bool = True) -> FastAPI:
    resolved = load_settings(_env_file=None)
    app = create_app(resolved)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def _boss() -> BossSession:
        return BossSession(session_id="test-session", email=resolved.boss_email)

    app.dependency_overrides[get_db] = _db
    if signed_in:
        app.dependency_overrides[require_boss] = _boss
    return app


async def _client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as c:
        yield c


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    async for c in _client(build_test_app(db_session)):
        yield c


@pytest.fixture
async def anon_client(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    async for c in _client(build_test_app(db_session, signed_in=False)):
        yield c


def app_of(client: httpx.AsyncClient) -> FastAPI:
    transport = getattr(client, "_transport")  # noqa: B009
    return cast(FastAPI, transport.app)


@pytest.fixture
def tg_app(client: httpx.AsyncClient, bot: RecordingBot) -> FastAPI:
    app = app_of(client)
    app.state.bot = bot
    return app
