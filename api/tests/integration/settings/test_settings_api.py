import datetime as dt
from decimal import Decimal
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Account,
    BusinessSettings,
    EntrySource,
    EntryStatus,
    JournalEntry,
    JournalLine,
)
from bookkeeper.settings_service import get_settings

pytestmark = pytest.mark.integration

FULL: dict[str, Any] = {
    "name": "Kopi Corner",
    "currency": "SGD",
    "timezone": "Asia/Singapore",
    "fy_start_month": 4,
    "gst_registered": True,
    "gst_rate": "9",
    "price_rule": "any_change",
    "dup_window_days": 120,
    "reminder_days": 5,
    "recap_time": "20:30",
    "report_day": 2,
    "report_time": "08:15",
}


async def test_get_before_setup_reports_not_configured(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/settings")

    assert res.status_code == 200
    body = res.json()
    assert body["configured"] is False
    assert body["settings"] is None
    assert body["defaults"]["currency"] == "SGD"
    assert body["defaults"]["recap_time"] == "21:00"


async def test_t017_defaults_sgd_and_singapore(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    res = await client.put("/api/settings", json={"name": "Kopi Corner"})

    assert res.status_code == 200
    body = res.json()
    assert body["currency"] == "SGD"
    assert body["timezone"] == "Asia/Singapore"
    assert Decimal(body["gst_rate"]) == Decimal("9")
    assert body["price_rule"] == "any_change"
    assert body["dup_window_days"] == 180
    assert body["reminder_days"] == 3
    assert body["recap_time"] == "21:00"
    assert body["report_day"] == 1
    assert body["report_time"] == "09:00"

    row = (await db_session.scalars(select(BusinessSettings))).one()
    assert row.currency == "SGD"
    assert row.timezone == "Asia/Singapore"


async def test_put_updates_existing_row(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await client.put("/api/settings", json={"name": "Kopi Corner"})
    res = await client.put("/api/settings", json=FULL)

    assert res.status_code == 200
    assert await db_session.scalar(select(func.count()).select_from(BusinessSettings)) == 1
    got = (await client.get("/api/settings")).json()
    assert got["configured"] is True
    assert got["settings"]["recap_time"] == "20:30"
    assert got["settings"]["fy_start_month"] == 4


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("gst_rate", 150),
        ("gst_rate", -1),
        ("recap_time", "25:00"),
        ("recap_time", "9pm"),
        ("report_time", "9:00"),
        ("timezone", "Mars/Base"),
        ("fy_start_month", 13),
    ],
)
async def test_t035_invalid_rejected_and_nothing_saved(
    client: httpx.AsyncClient, field: str, value: Any
) -> None:
    await client.put("/api/settings", json=FULL)
    before = (await client.get("/api/settings")).json()["settings"]

    bad = {**FULL, "name": "Changed Name", "reminder_days": 9, field: value}
    res = await client.put("/api/settings", json=bad)

    assert res.status_code == 422
    assert [e["loc"] for e in res.json()["detail"]] == [["body", field]]
    after = (await client.get("/api/settings")).json()["settings"]
    assert after == before


async def test_t035_invalid_first_run_creates_nothing(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    res = await client.put("/api/settings", json={"name": "Kopi", "gst_rate": 150})

    assert res.status_code == 422
    assert await db_session.scalar(select(func.count()).select_from(BusinessSettings)) == 0
    assert await db_session.scalar(select(func.count()).select_from(Account)) == 0


async def test_t036_posted_entry_not_recalculated_on_gst_change(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await client.put("/api/settings", json=FULL)
    codes = {a.name: a.id for a in (await db_session.scalars(select(Account))).all()}
    entry = JournalEntry(
        entry_no=1043,
        date=dt.date(2026, 11, 10),
        description="Ocean Fresh INV-1043",
        source=EntrySource.AUTO,
        status=EntryStatus.POSTED,
        posted_at=dt.datetime(2026, 11, 10, 2, 0, tzinfo=dt.UTC),
    )
    db_session.add(entry)
    await db_session.flush()
    db_session.add_all(
        [
            JournalLine(
                entry_id=entry.id,
                line_no=1,
                account_id=codes["COGS Seafood"],
                debit=Decimal("400.00"),
                credit=Decimal("0"),
            ),
            JournalLine(
                entry_id=entry.id,
                line_no=2,
                account_id=codes["Input GST"],
                debit=Decimal("36.00"),
                credit=Decimal("0"),
            ),
            JournalLine(
                entry_id=entry.id,
                line_no=3,
                account_id=codes["Accounts Payable"],
                debit=Decimal("0"),
                credit=Decimal("436.00"),
            ),
        ]
    )
    await db_session.commit()

    res = await client.put("/api/settings", json={**FULL, "gst_rate": "8"})
    assert res.status_code == 200

    gst_line = await db_session.scalar(
        select(JournalLine.debit)
        .where(JournalLine.entry_id == entry.id)
        .where(JournalLine.account_id == codes["Input GST"])
        .execution_options(populate_existing=True)
    )
    assert gst_line == Decimal("36.00")
    current = await get_settings(db_session)
    assert current is not None
    assert current.gst_rate == Decimal("8.00")


async def test_get_settings_none_before_setup(db_session: AsyncSession) -> None:
    assert await get_settings(db_session) is None
