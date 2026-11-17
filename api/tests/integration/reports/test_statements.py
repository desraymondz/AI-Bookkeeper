import datetime as dt

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account, AccountType
from bookkeeper.reports import balance_sheet, profit_and_loss, trial_balance
from tests.integration.reports.helpers import ZERO, d, post, seed_three_months

pytestmark = pytest.mark.integration


async def test_trial_balance_lists_non_zero_accounts_and_totals_agree(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    await seed_three_months(db_session, ids)
    tb = await trial_balance(db_session, dt.date(2026, 9, 30))
    assert tb.total_debit == tb.total_credit
    assert tb.difference == ZERO
    codes = [r.code for r in tb.rows]
    assert codes == sorted(codes)
    assert "2000" not in codes
    cash = next(r for r in tb.rows if r.code == "1000")
    assert (cash.debit, cash.credit) == (d("5800.00"), ZERO)
    accum = next(r for r in tb.rows if r.code == "1510")
    assert (accum.debit, accum.credit) == (ZERO, d("100.00"))


async def test_unadjusted_excludes_adjusting_entries(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    await seed_three_months(db_session, ids)
    day = dt.date(2026, 9, 30)
    unadjusted = await trial_balance(db_session, day, adjusted=False)
    adjusted = await trial_balance(db_session, day, adjusted=True)
    assert "1510" not in [r.code for r in unadjusted.rows]
    assert "6200" not in [r.code for r in unadjusted.rows]
    assert "1510" in [r.code for r in adjusted.rows]
    assert unadjusted.difference == ZERO
    assert adjusted.total_debit - unadjusted.total_debit == d("100.00")


async def test_profit_and_loss_sections(db_session: AsyncSession, ids: dict[str, int]) -> None:
    await seed_three_months(db_session, ids)
    other = Account(
        code="7000", name="Interest Income", type=AccountType.REVENUE, subtype="other_income"
    )
    db_session.add(other)
    await db_session.flush()
    ids["7000"] = other.id
    await post(
        db_session,
        ids,
        dt.date(2026, 10, 28),
        "Interest",
        [("1010", "12.00", "0"), ("7000", "0", "12.00")],
    )
    pnl = await profit_and_loss(db_session, dt.date(2026, 10, 1), dt.date(2026, 10, 31))
    assert pnl.total_revenue == d("2000.00")
    assert pnl.total_cogs == d("400.00")
    assert pnl.gross_profit == d("1600.00")
    assert pnl.total_operating_expenses == d("1600.00")
    assert pnl.operating_profit == ZERO
    assert [(ln.name, ln.amount) for ln in pnl.other_items] == [("Interest Income", d("12.00"))]
    assert pnl.net_profit == d("12.00")


async def test_balance_sheet_balances_before_any_closing_entry(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    await seed_three_months(db_session, ids)
    sheet = await balance_sheet(db_session, dt.date(2026, 11, 30))
    assert sheet.balanced
    assert sheet.difference == ZERO
    assert sheet.total_assets == sheet.total_liabilities_and_equity
    earnings = next(ln for ln in sheet.equity if ln.account_id is None)
    assert earnings.amount == ZERO
    assert [ln.name for ln in sheet.fixed_assets] == ["Equipment", "Accumulated Depreciation"]
    assert sheet.total_fixed_assets == d("3600.00") - d("300.00")


async def test_balance_sheet_earnings_flow_into_equity(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    await post(
        db_session,
        ids,
        dt.date(2026, 11, 2),
        "Sale",
        [("1000", "300.00", "0"), ("4000", "0", "300.00")],
    )
    sheet = await balance_sheet(db_session, dt.date(2026, 11, 30))
    earnings = next(ln for ln in sheet.equity if ln.account_id is None)
    assert earnings.amount == d("300.00")
    assert sheet.balanced
