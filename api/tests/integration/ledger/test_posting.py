"""T-003, T-005 and G-7 posting audit. See planning/04-test-spec.md."""

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    AuditActor,
    AuditLog,
    EntryKind,
    EntrySource,
    EntryStatus,
    JournalEntry,
    JournalLine,
)
from bookkeeper.ledger import (
    EntryDraft,
    EntryStateError,
    LineDraft,
    UnbalancedEntryError,
    hold_entry,
    post_entry,
    post_held,
    reject_held,
    reverse,
    revise_held,
)
from tests.integration.ledger.conftest import Accounts, counts, invoice_draft, seed_entry_no

pytestmark = pytest.mark.integration


async def test_t003_amounts_read_back_exactly(db_session: AsyncSession, accounts: Accounts) -> None:
    entry = await post_entry(
        db_session,
        EntryDraft(
            date=dt.date(2026, 11, 18),
            description="Cents",
            lines=[
                LineDraft(account_id=accounts.cash, debit=Decimal("0.10")),
                LineDraft(account_id=accounts.bank, debit=Decimal("0.20")),
                LineDraft(account_id=accounts.sales, credit=Decimal("0.30")),
            ],
            source=EntrySource.MANUAL,
        ),
    )
    db_session.expunge_all()

    lines = (
        await db_session.scalars(
            select(JournalLine)
            .where(JournalLine.entry_id == entry.id)
            .order_by(JournalLine.line_no)
        )
    ).all()

    assert [str(line.debit) for line in lines] == ["0.10", "0.20", "0.00"]
    assert [str(line.credit) for line in lines] == ["0.00", "0.00", "0.30"]
    assert all(isinstance(line.debit, Decimal) for line in lines)


async def test_posting_numbers_sequentially_and_audits(
    db_session: AsyncSession, accounts: Accounts
) -> None:
    await seed_entry_no(db_session, 7)

    first = await post_entry(db_session, invoice_draft(accounts, gst=Decimal("36.00")))
    second = await post_entry(
        db_session, invoice_draft(accounts, source=EntrySource.MANUAL), actor=AuditActor.BOSS
    )

    assert (first.entry_no, second.entry_no) == (8, 9)
    assert first.status == EntryStatus.POSTED
    assert first.posted_at is not None
    assert first.period_id is not None
    audits = (
        await db_session.scalars(
            select(AuditLog).where(AuditLog.action == "entry.posted").order_by(AuditLog.id)
        )
    ).all()
    assert [a.ref_id for a in audits] == [str(first.id), str(second.id)]
    assert [a.actor for a in audits] == [AuditActor.AGENT, AuditActor.BOSS]
    assert audits[0].ref_type == "journal_entry"
    assert audits[0].detail_json["entry_no"] == "JE-00008"
    assert audits[0].detail_json["total"] == "436.00"


UNBALANCED = [
    (EntrySource.AUTO, EntryKind.NORMAL),
    (EntrySource.MANUAL, EntryKind.NORMAL),
    (EntrySource.MANUAL, EntryKind.OPENING),
    (EntrySource.SYSTEM, EntryKind.ADJUSTING),
    (EntrySource.BOSS_APPROVED, EntryKind.NORMAL),
]


@pytest.mark.parametrize(
    ("source", "kind"),
    UNBALANCED,
    ids=["auto-post", "manual-confirm", "opening-balance", "depreciation", "boss-direct"],
)
async def test_t005_unbalanced_new_entry_writes_nothing(
    db_session: AsyncSession, accounts: Accounts, source: EntrySource, kind: EntryKind
) -> None:
    before = await counts(db_session)
    draft = EntryDraft(
        date=dt.date(2026, 11, 10),
        description="Unbalanced",
        lines=[
            LineDraft(account_id=accounts.cogs_seafood, debit=Decimal("400.00")),
            LineDraft(account_id=accounts.input_gst, debit=Decimal("36.00")),
            LineDraft(account_id=accounts.ap, credit=Decimal("435.00")),
        ],
        source=source,
        kind=kind,
    )

    with pytest.raises(UnbalancedEntryError):
        await post_entry(db_session, draft)

    assert await counts(db_session) == before
    audits = await db_session.scalars(select(AuditLog).where(AuditLog.action == "entry.posted"))
    assert audits.all() == []


async def test_t005_unbalanced_sales_confirm_writes_nothing(
    db_session: AsyncSession, accounts: Accounts
) -> None:
    before = await counts(db_session)
    draft = EntryDraft(
        date=dt.date(2026, 11, 10),
        description="Sales 10 Nov",
        lines=[
            LineDraft(account_id=accounts.cash, debit=Decimal("420.00")),
            LineDraft(account_id=accounts.bank, debit=Decimal("1430.00")),
            LineDraft(account_id=accounts.sales, credit=Decimal("1697.25")),
            LineDraft(account_id=accounts.output_gst, credit=Decimal("152.76")),
        ],
        source=EntrySource.MANUAL,
    )

    with pytest.raises(UnbalancedEntryError):
        await post_entry(db_session, draft)

    assert await counts(db_session) == before


async def test_t005_unbalanced_boss_approval_of_held_entry_writes_nothing(
    db_session: AsyncSession, accounts: Accounts
) -> None:
    held = await hold_entry(db_session, invoice_draft(accounts, gst=Decimal("35.00")))
    before = await counts(db_session)

    with pytest.raises(UnbalancedEntryError) as err:
        await post_held(db_session, held.id, source=EntrySource.BOSS_APPROVED)

    assert err.value.difference == Decimal("1.00")
    assert await counts(db_session) == before
    await db_session.refresh(held)
    assert held.status == EntryStatus.PENDING_APPROVAL
    assert held.entry_no is None


async def test_t005_unbalanced_reversal_writes_nothing(
    db_session: AsyncSession, accounts: Accounts
) -> None:
    corrupt_id = await db_session.scalar(
        text(
            "INSERT INTO journal_entries (date, description, source, status, kind) "
            "VALUES (DATE '2026-11-01', 'Corrupt', 'manual', 'proposed', 'normal') RETURNING id"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO journal_lines (entry_id, line_no, account_id, debit, credit) VALUES "
            "(:e, 1, :a, 10.00, 0), (:e, 2, :b, 0, 9.00)"
        ),
        {"e": corrupt_id, "a": accounts.cash, "b": accounts.sales},
    )
    await db_session.execute(
        text("UPDATE journal_entries SET status = 'posted', entry_no = 500 WHERE id = :e"),
        {"e": corrupt_id},
    )
    before = await counts(db_session)

    with pytest.raises(UnbalancedEntryError):
        await reverse(db_session, int(corrupt_id or 0))

    assert await counts(db_session) == before


async def test_held_entry_lifecycle(db_session: AsyncSession, accounts: Accounts) -> None:
    held = await hold_entry(db_session, invoice_draft(accounts, gst=Decimal("35.00")))
    assert held.status == EntryStatus.PENDING_APPROVAL

    await revise_held(db_session, held.id, invoice_draft(accounts))
    posted = await post_held(db_session, held.id, source=EntrySource.BOSS_APPROVED)

    assert posted.status == EntryStatus.POSTED
    assert posted.source == EntrySource.BOSS_APPROVED
    lines = (
        await db_session.scalars(select(JournalLine).where(JournalLine.entry_id == held.id))
    ).all()
    assert sorted(line.debit for line in lines) == [
        Decimal("0.00"),
        Decimal("36.00"),
        Decimal("400.00"),
    ]
    with pytest.raises(EntryStateError):
        await post_held(db_session, held.id)
    with pytest.raises(EntryStateError):
        await reject_held(db_session, held.id)


async def test_reject_held(db_session: AsyncSession, accounts: Accounts) -> None:
    held = await hold_entry(db_session, invoice_draft(accounts))

    rejected = await reject_held(db_session, held.id)

    assert rejected.status == EntryStatus.REJECTED
    assert rejected.entry_no is None
    with pytest.raises(EntryStateError):
        await post_held(db_session, held.id)


async def test_refused_post_inside_caller_transaction_keeps_earlier_work(
    db_session: AsyncSession, accounts: Accounts
) -> None:
    kept = await post_entry(db_session, invoice_draft(accounts))
    held = await hold_entry(db_session, invoice_draft(accounts, gst=Decimal("1.00")))

    with pytest.raises(UnbalancedEntryError):
        await post_held(db_session, held.id)

    entry = await db_session.get(JournalEntry, kept.id)
    assert entry is not None
    assert entry.status == EntryStatus.POSTED
