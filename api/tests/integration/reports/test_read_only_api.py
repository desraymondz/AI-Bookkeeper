"""T-020. See planning/01-prd.md#global-rules (G-8)."""

import datetime as dt

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Bill, JournalEntry, JournalLine, Payment, Period
from tests.support.factories import post, seeded_chart

PATHS = (
    "/api/journal",
    "/api/journal/JE-00001",
    "/api/ledger/1",
    "/api/bills",
    "/api/bills/1",
    "/api/payments",
    "/api/periods",
    "/api/periods/2026-11",
)


async def _counts(session: AsyncSession) -> list[int | None]:
    return [
        await session.scalar(select(func.count()).select_from(model))
        for model in (JournalEntry, JournalLine, Bill, Payment, Period)
    ]


async def test_t020_web_api_refuses_book_writes(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await seeded_chart(db_session)
    await post(db_session, dt.date(2026, 11, 2), [("Cash", "10.00", "0"), ("Sales", "0", "10.00")])
    before = await _counts(db_session)
    for path in PATHS:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            res = await client.request(method, path, json={"status": "rejected", "amount": "0"})
            assert res.status_code in (404, 405), (method, path, res.status_code)
    assert await _counts(db_session) == before
    res = await client.get("/api/journal/JE-00001")
    assert res.status_code == 200


async def test_t187_year_to_date_uses_financial_year_start(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    from bookkeeper.ledger.periods import business_today
    from tests.support.factories import settings_row

    await settings_row(db_session, fy_start_month=4)
    today = await business_today(db_session)
    res = await client.get("/api/journal", params={"preset": "ytd"})
    assert res.status_code == 200
    year = today.year if today.month >= 4 else today.year - 1
    assert res.json()["start"] == f"{year}-04-01"
    assert res.json()["end"] == today.isoformat()
