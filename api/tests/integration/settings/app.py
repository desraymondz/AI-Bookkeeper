from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.config import load_settings
from bookkeeper.main import create_app
from bookkeeper.web_api import accounts, config, get_db, settings


def build_app(db_session: AsyncSession) -> FastAPI:
    app = create_app(load_settings(_env_file=None))
    for module in (settings, accounts, config):
        app.include_router(module.router)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    return app


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=build_app(db_session))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
