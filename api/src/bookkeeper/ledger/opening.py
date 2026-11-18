"""See planning/01-prd.md#f-004-opening-balances-web and planning/01-prd.md#global-rules (G-2)."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from bookkeeper.db.models import (
    AuditActor,
    EntryKind,
    EntrySource,
    EntryStatus,
    JournalEntry,
    JournalLine,
)
from bookkeeper.ledger.post import EntryDraft, LineDraft, check_lines, post_entry, reverse

DESCRIPTION = "Opening balances"


@dataclass(frozen=True, slots=True)
class OpeningLine:
    account_id: int
    debit: Decimal
    credit: Decimal


@dataclass(frozen=True, slots=True)
class OpeningState:
    entry: JournalEntry | None
    lines: list[OpeningLine]


@dataclass(frozen=True, slots=True)
class OpeningSaved:
    entry: JournalEntry
    reversed_entry: JournalEntry | None
    reversal: JournalEntry | None


async def current_opening(session: AsyncSession) -> JournalEntry | None:
    rev = aliased(JournalEntry)
    reversed_ids = select(rev.reverses_id).where(
        rev.kind == EntryKind.REVERSAL,
        rev.status == EntryStatus.POSTED,
        rev.reverses_id.is_not(None),
    )
    stmt = (
        select(JournalEntry)
        .where(
            JournalEntry.kind == EntryKind.OPENING,
            JournalEntry.status == EntryStatus.POSTED,
            JournalEntry.id.not_in(reversed_ids),
        )
        .order_by(JournalEntry.entry_no.desc())
        .limit(1)
    )
    return await session.scalar(stmt)


async def opening_state(session: AsyncSession) -> OpeningState:
    entry = await current_opening(session)
    if entry is None:
        return OpeningState(entry=None, lines=[])
    rows = await session.scalars(
        select(JournalLine).where(JournalLine.entry_id == entry.id).order_by(JournalLine.line_no)
    )
    return OpeningState(
        entry=entry,
        lines=[OpeningLine(r.account_id, r.debit, r.credit) for r in rows],
    )


async def save_opening(
    session: AsyncSession,
    as_at: dt.date,
    lines: list[LineDraft],
    *,
    actor: AuditActor = AuditActor.BOSS,
    now: dt.datetime | None = None,
) -> OpeningSaved:
    kept = [ln for ln in lines if ln.debit or ln.credit]
    check_lines(kept)
    async with session.begin_nested():
        previous = await current_opening(session)
        reversal = None
        if previous is not None:
            reversal = await reverse(
                session, previous.id, source=EntrySource.MANUAL, actor=actor, now=now
            )
        entry = await post_entry(
            session,
            EntryDraft(
                date=as_at,
                description=DESCRIPTION,
                lines=kept,
                source=EntrySource.MANUAL,
                kind=EntryKind.OPENING,
                reverses_id=previous.id if previous is not None else None,
            ),
            actor=actor,
            now=now,
        )
    return OpeningSaved(entry=entry, reversed_entry=previous, reversal=reversal)
