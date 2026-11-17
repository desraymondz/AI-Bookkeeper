import datetime as dt
from decimal import Decimal

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Bill, Payment, Supplier
from bookkeeper.reports import ap_aging
from tests.integration.reports.helpers import d
from tests.support.factories import post, supplier

pytestmark = pytest.mark.integration

AS_AT = dt.date(2026, 11, 18)


async def add_bill(session: AsyncSession, supplier: Supplier, amount: str, due: dt.date) -> Bill:
    bill = Bill(
        supplier_id=supplier.id,
        amount=Decimal(amount),
        due_date=due,
        created_at=dt.datetime(2026, 6, 1, tzinfo=dt.UTC),
    )
    session.add(bill)
    await session.flush()
    return bill


async def test_aging_buckets_and_payments(db_session: AsyncSession, ids: dict[str, int]) -> None:
    ocean = await supplier(db_session, "Ocean Fresh", "5000")
    dairy = await supplier(db_session, "Dairy Co", "5010")
    await add_bill(db_session, ocean, "100.00", dt.date(2026, 11, 30))
    await add_bill(db_session, ocean, "200.00", dt.date(2026, 11, 8))
    paid = await add_bill(db_session, dairy, "300.00", dt.date(2026, 9, 1))
    await add_bill(db_session, dairy, "50.00", dt.date(2026, 7, 1))
    entry = await post(
        db_session,
        dt.date(2026, 11, 1),
        [("2000", "300.00", "0"), ("1010", "0", "300.00")],
        description="Pay",
    )
    db_session.add(
        Payment(
            bill_id=paid.id, entry_id=entry.id, amount=d("300.00"), paid_on=dt.date(2026, 11, 1)
        )
    )
    await db_session.flush()

    report = await ap_aging(db_session, AS_AT)
    by_name = {r.supplier_name: r for r in report.suppliers}
    assert (by_name["Ocean Fresh"].current, by_name["Ocean Fresh"].days_1_30) == (
        d("100.00"),
        d("200.00"),
    )
    assert by_name["Dairy Co"].days_over_90 == d("50.00")
    assert by_name["Dairy Co"].total == d("50.00")
    assert report.totals.total == d("350.00")

    earlier = await ap_aging(db_session, dt.date(2026, 10, 15))
    assert {r.supplier_name: r.total for r in earlier.suppliers}["Dairy Co"] == d("350.00")


async def test_report_endpoints_respond_and_reject_writes(
    db_session: AsyncSession, ids: dict[str, int], client: httpx.AsyncClient
) -> None:
    await post(
        db_session,
        dt.date(2026, 11, 2),
        [("1000", "10.00", "0"), ("4000", "0", "10.00")],
        description="Sale",
    )
    for path in ("trial-balance", "adjusted-trial-balance", "ap-aging"):
        res = await client.get(f"/api/reports/{path}", params={"as_at": "2026-11-30"})
        assert res.status_code == 200, path
    for path in ("pnl", "balance-sheet", "cash-flow"):
        res = await client.get(
            f"/api/reports/{path}",
            params={"preset": "custom", "start": "2026-11-01", "end": "2026-11-30"},
        )
        assert res.status_code == 200, path
    pnl = await client.get("/api/reports/pnl", params={"start": "2026-11-01", "end": "2026-11-30"})
    assert pnl.json()["net_profit"] == "10.00"
    assert (await client.post("/api/reports/pnl")).status_code == 405
    assert (await client.get("/api/reports/pnl", params={"preset": "custom"})).status_code == 422
    assert (await client.get("/api/reports/pnl", params={"preset": "bogus"})).status_code == 422
