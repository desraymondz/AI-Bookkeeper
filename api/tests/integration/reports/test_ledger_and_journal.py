import datetime as dt

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.ledger import reverse
from bookkeeper.reports import general_ledger, journal_entry_detail, journal_listing
from tests.integration.reports.helpers import ZERO, d, post, seed_three_months

pytestmark = pytest.mark.integration


async def test_general_ledger_opening_running_and_closing(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    await seed_three_months(db_session, ids)
    gl = await general_ledger(db_session, ids["1000"], dt.date(2026, 10, 1), dt.date(2026, 10, 31))
    assert gl.opening_balance == d("5800.00")
    assert [p.balance for p in gl.postings] == [d("6600.00")]
    assert gl.total_debit == d("800.00")
    assert gl.closing_balance == d("6600.00")

    ap = await general_ledger(db_session, ids["2000"], dt.date(2026, 10, 1), dt.date(2026, 10, 31))
    assert ap.opening_balance == ZERO
    assert [p.balance for p in ap.postings] == [d("436.00"), ZERO]
    assert ap.closing_balance == ZERO


async def test_journal_totals_equal_and_account_filter(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    await seed_three_months(db_session, ids)
    listing = await journal_listing(db_session, dt.date(2026, 10, 1), dt.date(2026, 10, 31))
    assert len(listing.entries) == 5
    assert listing.total_debit == listing.total_credit
    only_ap = await journal_listing(
        db_session, dt.date(2026, 10, 1), dt.date(2026, 10, 31), account_id=ids["2000"]
    )
    assert [e.description for e in only_ap.entries] == ["Ocean Fresh invoice", "Pay Ocean Fresh"]


async def test_entry_detail_links_reversal_and_audit(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    original = await post(
        db_session,
        ids,
        dt.date(2026, 11, 4),
        "Wrong",
        [("6010", "50.00", "0"), ("1010", "0", "50.00")],
    )
    assert original.entry_no is not None
    reversal = await reverse(db_session, original.id)
    assert reversal.entry_no is not None
    detail = await journal_entry_detail(db_session, original.entry_no)
    assert detail is not None
    assert detail.reversed_by is not None
    assert detail.reversed_by.entry_no == f"JE-{reversal.entry_no:05d}"
    assert [a.action for a in detail.audit] == ["entry.posted"]
    back = await journal_entry_detail(db_session, reversal.entry_no)
    assert back is not None
    assert back.reverses is not None
    assert back.reverses.id == original.id
    assert await journal_entry_detail(db_session, 99999) is None


async def test_ledger_and_journal_api(
    db_session: AsyncSession, ids: dict[str, int], client: httpx.AsyncClient
) -> None:
    await seed_three_months(db_session, ids)
    res = await client.get(
        f"/api/ledger/{ids['1010']}",
        params={"preset": "custom", "start": "2026-09-01", "end": "2026-09-30"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["opening_balance"] == "0.00"
    assert body["closing_balance"] == "15664.00"

    res = await client.get("/api/journal", params={"start": "2026-11-01", "end": "2026-11-30"})
    assert res.status_code == 200
    assert res.json()["total_debit"] == res.json()["total_credit"]

    first = res.json()["entries"][0]["entry_no"]
    assert (await client.get(f"/api/journal/{first}")).status_code == 200
    assert (await client.get("/api/journal/JE-99999")).status_code == 404
    assert (await client.get("/api/journal/nonsense")).status_code == 404
    assert (await client.get("/api/ledger/987654")).status_code == 404
