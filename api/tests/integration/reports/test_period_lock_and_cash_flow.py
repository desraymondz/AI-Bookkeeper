import datetime as dt
from decimal import Decimal

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import EntryKind
from bookkeeper.ledger import lock_period
from bookkeeper.reports import cash_flow, trial_balance
from tests.integration.reports.helpers import ZERO, d, seed_three_months
from tests.support.factories import post

pytestmark = pytest.mark.integration

MONTHS = [
    (dt.date(2026, 9, 1), dt.date(2026, 9, 30)),
    (dt.date(2026, 10, 1), dt.date(2026, 10, 31)),
    (dt.date(2026, 11, 1), dt.date(2026, 11, 30)),
]


async def cash_and_bank(session: AsyncSession, as_at: dt.date) -> Decimal:
    tb = await trial_balance(session, as_at)
    return sum((r.debit - r.credit for r in tb.rows if r.code in {"1000", "1010"}), ZERO)


async def test_t009_locked_month_totals_do_not_move(
    db_session: AsyncSession, ids: dict[str, int], client: httpx.AsyncClient
) -> None:
    await seed_three_months(db_session)
    await lock_period(db_session, 2026, 10)
    urls = [
        "/api/reports/trial-balance?as_at=2026-10-31",
        "/api/reports/adjusted-trial-balance?as_at=2026-10-31",
    ]
    before = [(await client.get(u)).json() for u in urls]
    assert all(b["rows"] for b in before)

    await post(
        db_session,
        dt.date(2026, 11, 22),
        [("1000", "50.00", "0"), ("4000", "0", "50.00")],
        description="Late sale",
    )
    late = await post(
        db_session,
        dt.date(2026, 10, 15),
        [("6010", "75.00", "0"), ("2000", "0", "75.00")],
        description="Late invoice",
    )
    assert late.date == dt.date(2026, 11, 1)
    await post(
        db_session,
        dt.date(2026, 12, 2),
        [("6200", "100.00", "0"), ("1510", "0", "100.00")],
        description="Dec depreciation",
        kind=EntryKind.ADJUSTING,
    )

    after = [(await client.get(u)).json() for u in urls]
    assert after == before


@pytest.mark.parametrize(("start", "end"), MONTHS)
async def test_t202_net_change_equals_cash_and_bank_movement(
    db_session: AsyncSession, ids: dict[str, int], start: dt.date, end: dt.date
) -> None:
    await seed_three_months(db_session)
    flow = await cash_flow(db_session, start, end)
    opening = await cash_and_bank(db_session, start - dt.timedelta(days=1))
    closing = await cash_and_bank(db_session, end)
    assert flow.opening_cash == opening
    assert flow.closing_cash == closing
    assert flow.net_change == closing - opening
    assert flow.difference == ZERO


async def test_cash_flow_sections_for_the_first_month(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    await seed_three_months(db_session)
    flow = await cash_flow(db_session, dt.date(2026, 9, 1), dt.date(2026, 9, 30))
    assert flow.net_profit == ZERO
    assert flow.depreciation_addback == d("100.00")
    assert flow.payables_change == []
    assert [(ln.name, ln.amount) for ln in flow.other_working_capital] == [
        ("Input GST", d("-36.00"))
    ]
    assert flow.net_cash_from_operating == d("64.00")
    assert [(ln.name, ln.amount) for ln in flow.investing] == [("Equipment", d("-3600.00"))]
    assert [(ln.name, ln.amount) for ln in flow.financing] == [("Owner's Capital", d("25000.00"))]
    assert flow.net_change == d("21464.00")
    assert (flow.opening_cash, flow.closing_cash) == (ZERO, d("21464.00"))


async def test_cash_flow_reports_payables_movement(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    await seed_three_months(db_session)
    await post(
        db_session,
        dt.date(2026, 11, 25),
        [("5100", "600.00", "0"), ("2000", "0", "600.00")],
        description="Big invoice",
    )
    flow = await cash_flow(db_session, dt.date(2026, 11, 1), dt.date(2026, 11, 30))
    assert [(ln.name, ln.amount) for ln in flow.payables_change] == [
        ("Accounts Payable", d("600.00"))
    ]
    assert flow.net_profit == d("-600.00")
    assert flow.difference == ZERO
