from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.auth.wiring import include_protected
from bookkeeper.web_api import ledger as ledger_api
from bookkeeper.web_api import reports as reports_api
from tests.integration.reports.helpers import seed_chart
from tests.integration.settings.app import build_app


@pytest.fixture
async def ids(db_session: AsyncSession) -> dict[str, int]:
    return await seed_chart(db_session)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    app = build_app(db_session)
    include_protected(app, reports_api.router)
    include_protected(app, ledger_api.router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
