"""T-006, T-007. See planning/04-test-spec.md and planning/decisions.md#D-018."""

import datetime as dt
from collections.abc import Awaitable, Callable
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    AuditLog,
    EntryKind,
    EntrySource,
    EntryStatus,
    JournalEntry,
    JournalLine,
)
from bookkeeper.ledger import (
    AlreadyReversedError,
    EntryDraft,
    EntryStateError,
    ImmutableEntryError,
    LineDraft,
    correct,
    format_entry_no,
    hold_entry,
    post_entry,
    reverse,
)
from tests.integration.ledger.conftest import Accounts, invoice_draft, seed_entry_no

pytestmark = pytest.mark.integration

Snapshot = tuple[tuple[object, ...], list[tuple[object, ...]]]


async def snapshot(session: AsyncSession, entry_id: int) -> Snapshot:
    session.expunge_all()
    entry = await session.get(JournalEntry, entry_id)
    assert entry is not None
    head = (entry.entry_no, entry.date, entry.status, entry.description, entry.kind, entry.note)
    lines = (
        await session.scalars(
            select(JournalLine).where(JournalLine.entry_id == entry_id).order_by(JournalLine.id)
        )
    ).all()
    session.expunge_all()
    return head, [(ln.line_no, ln.account_id, ln.debit, ln.credit, ln.memo) for ln in lines]


async def post_je42(session: AsyncSession, acc: Accounts) -> JournalEntry:
    await seed_entry_no(session, 41)
    entry = await post_entry(session, invoice_draft(acc))
    assert format_entry_no(entry.entry_no or 0) == "JE-00042"
    return entry


async def first_line(session: AsyncSession, entry_id: int) -> JournalLine:
    line = await session.scalar(
        select(JournalLine).where(JournalLine.entry_id == entry_id).order_by(JournalLine.line_no)
    )
    assert line is not None
    return line


async def change_amount(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    line = await first_line(s, entry_id)
    line.debit = Decimal("399.00")


async def change_account(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    line = await first_line(s, entry_id)
    line.account_id = acc.cash


async def delete_line(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    await s.delete(await first_line(s, entry_id))


async def add_line(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    s.add(JournalLine(entry_id=entry_id, line_no=9, account_id=acc.cash, debit=Decimal("1.00")))


async def change_date(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    entry = await s.get(JournalEntry, entry_id)
    assert entry is not None
    entry.date = dt.date(2026, 11, 11)


async def change_status(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    entry = await s.get(JournalEntry, entry_id)
    assert entry is not None
    entry.status = EntryStatus.REJECTED


async def change_description(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    entry = await s.get(JournalEntry, entry_id)
    assert entry is not None
    entry.description = "Edited"


async def delete_entry(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    entry = await s.get(JournalEntry, entry_id)
    assert entry is not None
    await s.delete(entry)


async def bulk_update_lines(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    await s.execute(
        update(JournalLine).where(JournalLine.entry_id == entry_id).values(debit=Decimal("1.00"))
    )


async def bulk_delete_lines(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    await s.execute(delete(JournalLine).where(JournalLine.entry_id == entry_id))


async def bulk_update_entry(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    await s.execute(
        update(JournalEntry).where(JournalEntry.id == entry_id).values(date=dt.date(2026, 1, 1))
    )


async def bulk_delete_entry(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    await s.execute(delete(JournalEntry).where(JournalEntry.id == entry_id))


Attempt = Callable[[AsyncSession, int, Accounts], Awaitable[None]]


async def in_savepoint(s: AsyncSession, attempt: Attempt, entry_id: int, acc: Accounts) -> None:
    async with s.begin_nested():
        await attempt(s, entry_id, acc)
        await s.flush()


async def insert_posted(s: AsyncSession, entry_id: int, acc: Accounts) -> None:
    s.add(
        JournalEntry(
            date=dt.date(2026, 11, 1),
            description="Sneaky",
            source=EntrySource.MANUAL,
            status=EntryStatus.POSTED,
            entry_no=900,
        )
    )


@pytest.mark.parametrize(
    "attempt",
    [
        change_amount,
        change_account,
        delete_line,
        add_line,
        change_date,
        change_status,
        change_description,
        delete_entry,
        bulk_update_lines,
        bulk_delete_lines,
        bulk_update_entry,
        bulk_delete_entry,
    ],
)
async def test_t006_posted_entry_cannot_change(
    db_session: AsyncSession, accounts: Accounts, attempt: Attempt
) -> None:
    entry = await post_je42(db_session, accounts)
    before = await snapshot(db_session, entry.id)

    with pytest.raises(ImmutableEntryError):
        await in_savepoint(db_session, attempt, entry.id, accounts)

    assert await snapshot(db_session, entry.id) == before


async def test_t007_correction_posts_reversal_and_new_entry(
    db_session: AsyncSession, accounts: Accounts
) -> None:
    original = await post_je42(db_session, accounts)
    before = await snapshot(db_session, original.id)
    fixed = EntryDraft(
        date=dt.date(2026, 11, 12),
        description="Ocean Fresh INV-1043 corrected",
        lines=[
            LineDraft(account_id=accounts.cogs_seafood, debit=Decimal("396.00")),
            LineDraft(account_id=accounts.input_gst, debit=Decimal("35.64")),
            LineDraft(account_id=accounts.ap, credit=Decimal("431.64")),
        ],
        source=EntrySource.BOSS_APPROVED,
    )

    reversal, new = await correct(db_session, original.id, fixed)

    assert reversal.kind == EntryKind.REVERSAL
    assert reversal.reverses_id == original.id
    assert new.reverses_id == original.id
    assert new.kind == EntryKind.NORMAL
    assert reversal.status == new.status == EntryStatus.POSTED
    assert (reversal.entry_no, new.entry_no) == (43, 44)
    assert "JE-00042" in reversal.description

    orig_lines = before[1]
    rev_lines = (await snapshot(db_session, reversal.id))[1]
    assert [(a, d, c) for _, a, d, c, _ in rev_lines] == [(a, c, d) for _, a, d, c, _ in orig_lines]
    assert await snapshot(db_session, original.id) == before
    new_lines = (await snapshot(db_session, new.id))[1]
    assert [d for _, _, d, _, _ in new_lines] == [
        Decimal("396.00"),
        Decimal("35.64"),
        Decimal("0.00"),
    ]

    actions = (await db_session.scalars(select(AuditLog.action).order_by(AuditLog.id))).all()
    assert actions.count("entry.posted") == 2
    assert actions.count("entry.reversed") == 1


async def test_reverse_twice_refused(db_session: AsyncSession, accounts: Accounts) -> None:
    original = await post_entry(db_session, invoice_draft(accounts))
    await reverse(db_session, original.id)

    with pytest.raises(AlreadyReversedError):
        await reverse(db_session, original.id)
    with pytest.raises(AlreadyReversedError):
        await correct(db_session, original.id, invoice_draft(accounts))


async def test_reverse_unposted_refused(db_session: AsyncSession, accounts: Accounts) -> None:
    held = await hold_entry(db_session, invoice_draft(accounts))

    with pytest.raises(EntryStateError):
        await reverse(db_session, held.id)


async def test_direct_posted_insert_refused(db_session: AsyncSession, accounts: Accounts) -> None:
    with pytest.raises(ImmutableEntryError):
        await in_savepoint(db_session, insert_posted, 0, accounts)
