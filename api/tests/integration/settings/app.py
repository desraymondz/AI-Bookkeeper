from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.auth.deps import BossSession, require_boss
from bookkeeper.config import load_settings
from bookkeeper.main import create_app
from bookkeeper.web_api import get_db


def build_app(db_session: AsyncSession, *, signed_in: bool = True) -> FastAPI:
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


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=build_app(db_session))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
