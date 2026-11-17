import asyncio
import datetime as dt
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account, EntryKind, EntrySource
from bookkeeper.db.session import create_engine
from bookkeeper.ledger import EntryDraft, LineDraft, post_entry
from bookkeeper.ledger.coa import seed_default_chart
from bookkeeper.reports import balance_sheet, cash_flow, trial_balance

pytestmark = pytest.mark.integration

START = dt.date(2026, 10, 1)
END = dt.date(2026, 12, 31)
ACCOUNT_COUNT = 18

amounts = st.integers(min_value=1, max_value=500_000).map(lambda c: Decimal(c) / 100)
sides = st.tuples(st.integers(0, ACCOUNT_COUNT - 1), amounts)


@st.composite
def entries(draw: st.DrawFn) -> tuple[dt.date, EntryKind, list[tuple[int, Decimal, Decimal]]]:
    day = START + dt.timedelta(days=draw(st.integers(0, (END - START).days)))
    kind = draw(st.sampled_from([EntryKind.NORMAL, EntryKind.NORMAL, EntryKind.ADJUSTING]))
    debits = draw(st.lists(sides, min_size=1, max_size=3))
    credits = draw(st.lists(sides, min_size=1, max_size=3))
    total_debit = sum((a for _, a in debits), Decimal(0))
    total_credit = sum((a for _, a in credits), Decimal(0))
    lines = [(i, a, Decimal(0)) for i, a in debits] + [(i, Decimal(0), a) for i, a in credits]
    gap = total_debit - total_credit
    if gap > 0:
        lines.append((draw(st.integers(0, ACCOUNT_COUNT - 1)), Decimal(0), gap))
    elif gap < 0:
        lines.append((draw(st.integers(0, ACCOUNT_COUNT - 1)), -gap, Decimal(0)))
    return day, kind, lines


ranges = st.tuples(st.integers(0, 91), st.integers(0, 91)).map(
    lambda p: (START + dt.timedelta(days=min(p)), START + dt.timedelta(days=max(p)))
)


async def check_identities(
    database_url: str,
    plan: list[tuple[dt.date, EntryKind, list[tuple[int, Decimal, Decimal]]]],
    window: tuple[dt.date, dt.date],
) -> None:
    engine = create_engine(database_url)
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            session = AsyncSession(
                bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            try:
                await seed_default_chart(session)
                rows = await session.execute(select(Account.id).order_by(Account.code))
                account_ids = [r[0] for r in rows.all()]
                for day, kind, lines in plan:
                    draft = EntryDraft(
                        date=day,
                        description="Generated",
                        lines=[LineDraft(account_ids[i], dr, cr) for i, dr, cr in lines],
                        source=EntrySource.MANUAL,
                        kind=kind,
                    )
                    await post_entry(session, draft)
                start, end = window
                for adjusted in (True, False):
                    tb = await trial_balance(session, end, adjusted=adjusted)
                    assert tb.total_debit == tb.total_credit
                    assert tb.difference == 0
                sheet = await balance_sheet(session, end)
                assert sheet.total_assets == sheet.total_liabilities_and_equity
                assert sheet.balanced
                flow = await cash_flow(session, start, end)
                assert flow.net_change == flow.closing_cash - flow.opening_cash
                assert flow.difference == 0
            finally:
                await session.close()
                await trans.rollback()
    finally:
        await engine.dispose()


@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(plan=st.lists(entries(), min_size=1, max_size=8), window=ranges)
def test_statement_identities_hold_for_random_balanced_postings(
    database_url: str,
    plan: list[tuple[dt.date, EntryKind, list[tuple[int, Decimal, Decimal]]]],
    window: tuple[dt.date, dt.date],
) -> None:
    asyncio.run(check_identities(database_url, plan, window))
