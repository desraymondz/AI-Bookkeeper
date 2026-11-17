"""See planning/decisions.md#D-030 (payables found by subtype)."""

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account, AccountType
from bookkeeper.reports import cash_flow
from tests.support.factories import post, seeded_chart


async def test_payables_follow_subtype_not_name(db_session: AsyncSession) -> None:
    await seeded_chart(db_session)
    db_session.add_all(
        [
            Account(
                code="2050",
                name="Trade Creditors",
                type=AccountType.LIABILITY,
                subtype="trade_payable",
            ),
            Account(
                code="2060",
                name="Staff Payable",
                type=AccountType.LIABILITY,
                subtype="current_liability",
            ),
        ]
    )
    await db_session.flush()
    day = dt.date(2026, 11, 10)
    await post(db_session, day, [("5100", "100.00", "0"), ("2050", "0", "100.00")])
    await post(db_session, day, [("6020", "50.00", "0"), ("2060", "0", "50.00")])

    flow = await cash_flow(db_session, dt.date(2026, 11, 1), dt.date(2026, 11, 30))

    assert [ln.name for ln in flow.payables_change] == ["Trade Creditors"]
    assert [ln.name for ln in flow.other_working_capital] == ["Staff Payable"]
    assert flow.difference == 0
