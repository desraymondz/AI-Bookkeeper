"""T-008, T-236. See planning/04-test-spec.md and planning/decisions.md#D-024."""

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    BusinessSettings,
    EntryKind,
    EntrySource,
    EntryStatus,
    JournalEntry,
    Period,
    PeriodStatus,
)
from bookkeeper.ledger import (
    EntryDraft,
    LineDraft,
    business_today,
    first_open_period,
    hold_entry,
    is_locked,
    lock_period,
    post_entry,
    post_held,
    reverse,
)
from tests.integration.ledger.conftest import Accounts, invoice_draft

pytestmark = pytest.mark.integration

OCT_15 = dt.date(2026, 10, 15)
NOV_1 = dt.date(2026, 11, 1)


async def entries_in_october(session: AsyncSession) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(JournalEntry)
        .where(
            JournalEntry.date >= dt.date(2026, 10, 1),
            JournalEntry.date < NOV_1,
            JournalEntry.status == EntryStatus.POSTED,
        )
    )
    return int(count or 0)


def balanced(acc: Accounts, source: EntrySource, kind: EntryKind) -> EntryDraft:
    return EntryDraft(
        date=OCT_15,
        description=f"{source.value} {kind.value}",
        lines=[
            LineDraft(account_id=acc.depreciation, debit=Decimal("50.00")),
            LineDraft(account_id=acc.accum_depreciation, credit=Decimal("50.00")),
        ],
        source=source,
        kind=kind,
        note="Caller note",
    )


@pytest.mark.parametrize(
    ("source", "kind"),
    [
        (EntrySource.AUTO, EntryKind.NORMAL),
        (EntrySource.BOSS_APPROVED, EntryKind.NORMAL),
        (EntrySource.MANUAL, EntryKind.NORMAL),
        (EntrySource.MANUAL, EntryKind.OPENING),
        (EntrySource.SYSTEM, EntryKind.ADJUSTING),
    ],
)
async def test_t008_locked_period_moves_to_first_open(
    db_session: AsyncSession, accounts: Accounts, source: EntrySource, kind: EntryKind
) -> None:
    await lock_period(db_session, 2026, 10)

    entry = await post_entry(db_session, balanced(accounts, source, kind))

    assert entry.date == NOV_1
    assert entry.note is not None
    assert "15 Oct 2026" in entry.note
    assert "Caller note" in entry.note
    period = await db_session.get(Period, entry.period_id)
    assert period is not None
    assert (period.year, period.month, period.status) == (2026, 11, PeriodStatus.OPEN)
    assert await entries_in_october(db_session) == 0


async def test_t008_reversal_of_locked_entry_moves(
    db_session: AsyncSession, accounts: Accounts
) -> None:
    original = await post_entry(db_session, invoice_draft(accounts, date=OCT_15))
    assert original.date == OCT_15
    await lock_period(db_session, 2026, 10)

    reversal = await reverse(db_session, original.id)

    assert reversal.date == NOV_1
    assert reversal.note is not None
    assert "15 Oct 2026" in reversal.note
    assert await entries_in_october(db_session) == 1


async def test_t008_skips_consecutive_locked_periods(
    db_session: AsyncSession, accounts: Accounts
) -> None:
    await lock_period(db_session, 2026, 10)
    await lock_period(db_session, 2026, 11)

    entry = await post_entry(db_session, balanced(accounts, EntrySource.AUTO, EntryKind.NORMAL))

    assert entry.date == dt.date(2026, 12, 1)
    assert entry.note is not None
    assert "15 Oct 2026" in entry.note


async def test_t236_held_october_invoice_approved_into_november(
    db_session: AsyncSession, accounts: Accounts
) -> None:
    held = await hold_entry(db_session, invoice_draft(accounts, date=OCT_15))
    await lock_period(db_session, 2026, 10)
    nov = await first_open_period(db_session, OCT_15)
    assert (nov.year, nov.month, nov.status) == (2026, 11, PeriodStatus.OPEN)

    posted = await post_held(db_session, held.id, source=EntrySource.BOSS_APPROVED)

    assert posted.date == NOV_1
    assert posted.note is not None
    assert "15 Oct 2026" in posted.note
    assert posted.period_id == nov.id


async def test_open_period_keeps_date(db_session: AsyncSession, accounts: Accounts) -> None:
    entry = await post_entry(db_session, invoice_draft(accounts, date=OCT_15))

    assert entry.date == OCT_15
    assert entry.note is None
    assert not await is_locked(db_session, OCT_15)


async def test_lock_period_is_one_way_and_idempotent(db_session: AsyncSession) -> None:
    first = await lock_period(db_session, 2026, 10)
    again = await lock_period(db_session, 2026, 10)

    assert first.id == again.id
    assert again.status == PeriodStatus.LOCKED
    assert again.closed_at is not None
    assert await is_locked(db_session, OCT_15)


async def test_business_today_uses_settings_timezone(db_session: AsyncSession) -> None:
    late_utc = dt.datetime(2026, 10, 31, 17, 30, tzinfo=dt.UTC)

    assert await business_today(db_session, late_utc) == NOV_1

    db_session.add(BusinessSettings(name="Cafe", timezone="America/New_York"))
    await db_session.flush()

    assert await business_today(db_session, late_utc) == dt.date(2026, 10, 31)
