"""See planning/01-prd.md#global-rules (G-1, G-2, G-3, G-7), planning/decisions.md#D-018, #D-024."""

import datetime as dt
import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from decimal import Decimal

from sqlalchemy import func, select
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
from bookkeeper.ledger.errors import (
    AlreadyReversedError,
    EntryNotFoundError,
    EntryStateError,
    InvalidAmountError,
    InvalidEntryError,
    TooFewLinesError,
    UnbalancedEntryError,
)
from bookkeeper.ledger.guard import authorize_posting
from bookkeeper.ledger.money import ZERO, to_money
from bookkeeper.ledger.periods import resolve_posting_date

ENTRY_NO_LOCK_KEY = 0x4B45_4E4F
HELD_STATUSES = (EntryStatus.PROPOSED, EntryStatus.PENDING_APPROVAL)
_ENTRY_NO = re.compile(r"^JE-(\d{5,})$")
_DEFAULT_ACTOR = {
    EntrySource.AUTO: AuditActor.AGENT,
    EntrySource.BOSS_APPROVED: AuditActor.BOSS,
    EntrySource.MANUAL: AuditActor.BOSS,
    EntrySource.SYSTEM: AuditActor.SYSTEM,
}


@dataclass(frozen=True, slots=True)
class LineDraft:
    account_id: int
    debit: Decimal = ZERO
    credit: Decimal = ZERO
    memo: str | None = None


@dataclass(frozen=True, slots=True)
class EntryDraft:
    date: dt.date
    description: str
    lines: Sequence[LineDraft]
    source: EntrySource
    kind: EntryKind = EntryKind.NORMAL
    invoice_id: int | None = None
    reverses_id: int | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class CheckedLine:
    account_id: int
    debit: Decimal
    credit: Decimal
    memo: str | None = field(default=None)


def format_entry_no(entry_no: int) -> str:
    return f"JE-{entry_no:05d}"


def parse_entry_no(label: str) -> int:
    match = _ENTRY_NO.match(label.strip().upper())
    if match is None:
        raise ValueError(f"{label!r} is not an entry number like JE-00042")
    return int(match.group(1))


def check_line_shapes(lines: Sequence[LineDraft]) -> list[CheckedLine]:
    checked: list[CheckedLine] = []
    for line_no, line in enumerate(lines, start=1):
        debit = to_money(line.debit, line_no=line_no)
        credit = to_money(line.credit, line_no=line_no)
        if debit < 0 or credit < 0:
            raise InvalidAmountError("amounts must not be negative", line_no=line_no)
        if (debit > 0) == (credit > 0):
            raise InvalidAmountError(
                "exactly one of debit or credit must be above 0", line_no=line_no
            )
        if isinstance(line.account_id, bool) or not isinstance(line.account_id, int):
            raise InvalidEntryError(f"Line {line_no}: account_id must be an integer")
        checked.append(CheckedLine(line.account_id, debit, credit, line.memo))
    return checked


def check_lines(lines: Sequence[LineDraft]) -> list[CheckedLine]:
    if len(lines) < 2:
        raise TooFewLinesError(len(lines))
    checked = check_line_shapes(lines)
    debits = sum((line.debit for line in checked), ZERO)
    credits = sum((line.credit for line in checked), ZERO)
    if debits != credits:
        raise UnbalancedEntryError(debits, credits)
    return checked


def _check_header(draft: EntryDraft) -> None:
    if not draft.description.strip():
        raise InvalidEntryError("An entry needs a description.")
    if not isinstance(draft.date, dt.date) or isinstance(draft.date, dt.datetime):
        raise InvalidEntryError("Entry date must be a date.")


def _join_notes(*notes: str | None) -> str | None:
    parts = [n.strip() for n in notes if n and n.strip()]
    return "; ".join(parts) or None


def _add_lines(session: AsyncSession, entry_id: int, lines: Sequence[CheckedLine]) -> None:
    session.add_all(
        JournalLine(
            entry_id=entry_id,
            line_no=line_no,
            account_id=line.account_id,
            debit=line.debit,
            credit=line.credit,
            memo=line.memo,
        )
        for line_no, line in enumerate(lines, start=1)
    )


async def _load_lines(session: AsyncSession, entry_id: int) -> list[JournalLine]:
    rows = await session.scalars(
        select(JournalLine)
        .where(JournalLine.entry_id == entry_id)
        .order_by(JournalLine.line_no, JournalLine.id)
        .execution_options(populate_existing=True)
    )
    return list(rows.all())


async def _get_for_update(session: AsyncSession, entry_id: int) -> JournalEntry:
    entry = await session.get(JournalEntry, entry_id, with_for_update=True, populate_existing=True)
    if entry is None:
        raise EntryNotFoundError(entry_id)
    return entry


async def _next_entry_no(session: AsyncSession) -> int:
    await session.execute(select(func.pg_advisory_xact_lock(ENTRY_NO_LOCK_KEY)))
    current = await session.scalar(select(func.coalesce(func.max(JournalEntry.entry_no), 0)))
    return int(current or 0) + 1


def _audit(
    session: AsyncSession,
    action: str,
    entry: JournalEntry,
    actor: AuditActor,
    detail: dict[str, object],
) -> None:
    session.add(
        AuditLog(
            actor=actor,
            action=action,
            ref_type="journal_entry",
            ref_id=str(entry.id),
            detail_json=detail,
        )
    )


async def _finalize(
    session: AsyncSession,
    entry: JournalEntry,
    lines: Sequence[CheckedLine],
    *,
    source: EntrySource,
    actor: AuditActor | None,
    now: dt.datetime | None,
) -> JournalEntry:
    target = await resolve_posting_date(session, entry.date)
    entry_no = await _next_entry_no(session)
    with authorize_posting(session.sync_session, entry):
        entry.date = target.date
        entry.period_id = target.period.id
        entry.note = _join_notes(entry.note, target.note)
        entry.source = source
        entry.status = EntryStatus.POSTED
        entry.entry_no = entry_no
        entry.posted_at = now or dt.datetime.now(dt.UTC)
        await session.flush()
    detail: dict[str, object] = {
        "entry_no": format_entry_no(entry_no),
        "date": target.date.isoformat(),
        "original_date": target.original_date.isoformat(),
        "source": source.value,
        "kind": entry.kind.value,
        "total": str(sum((line.debit for line in lines), ZERO)),
        "lines": [
            {"account_id": ln.account_id, "debit": str(ln.debit), "credit": str(ln.credit)}
            for ln in lines
        ],
        "invoice_id": entry.invoice_id,
        "reverses_id": entry.reverses_id,
    }
    action = "entry.reversed" if entry.kind == EntryKind.REVERSAL else "entry.posted"
    _audit(session, action, entry, actor or _DEFAULT_ACTOR[source], detail)
    await session.flush()
    return entry


async def _post_new(
    session: AsyncSession,
    draft: EntryDraft,
    *,
    actor: AuditActor | None,
    now: dt.datetime | None,
) -> JournalEntry:
    _check_header(draft)
    lines = check_lines(draft.lines)
    async with session.begin_nested():
        entry = JournalEntry(
            date=draft.date,
            description=draft.description,
            source=draft.source,
            status=EntryStatus.PROPOSED,
            kind=draft.kind,
            reverses_id=draft.reverses_id,
            invoice_id=draft.invoice_id,
            note=draft.note,
        )
        session.add(entry)
        await session.flush()
        _add_lines(session, entry.id, lines)
        await session.flush()
        return await _finalize(session, entry, lines, source=draft.source, actor=actor, now=now)


async def post_entry(
    session: AsyncSession,
    draft: EntryDraft,
    *,
    actor: AuditActor | None = None,
    now: dt.datetime | None = None,
) -> JournalEntry:
    if draft.kind == EntryKind.REVERSAL:
        raise InvalidEntryError("Reversals are posted only through reverse().")
    return await _post_new(session, draft, actor=actor, now=now)


async def hold_entry(
    session: AsyncSession,
    draft: EntryDraft,
    *,
    status: EntryStatus = EntryStatus.PENDING_APPROVAL,
    actor: AuditActor | None = None,
) -> JournalEntry:
    if status not in HELD_STATUSES:
        raise EntryStateError(f"Held entries are proposed or pending_approval, not {status}.")
    if draft.kind == EntryKind.REVERSAL:
        raise InvalidEntryError("Reversals are posted only through reverse().")
    _check_header(draft)
    lines = check_line_shapes(draft.lines)
    async with session.begin_nested():
        entry = JournalEntry(
            date=draft.date,
            description=draft.description,
            source=draft.source,
            status=status,
            kind=draft.kind,
            reverses_id=draft.reverses_id,
            invoice_id=draft.invoice_id,
            note=draft.note,
        )
        session.add(entry)
        await session.flush()
        _add_lines(session, entry.id, lines)
        _audit(
            session,
            "entry.held",
            entry,
            actor or _DEFAULT_ACTOR[draft.source],
            {"status": status.value, "date": draft.date.isoformat()},
        )
        await session.flush()
    return entry


async def _get_held(session: AsyncSession, entry_id: int) -> JournalEntry:
    entry = await _get_for_update(session, entry_id)
    if entry.status not in HELD_STATUSES:
        raise EntryStateError(f"Entry {entry_id} is {entry.status.value}, not held.")
    return entry


async def revise_held(
    session: AsyncSession,
    entry_id: int,
    draft: EntryDraft,
    *,
    actor: AuditActor | None = None,
) -> JournalEntry:
    if draft.kind == EntryKind.REVERSAL:
        raise InvalidEntryError("Reversals are posted only through reverse().")
    _check_header(draft)
    lines = check_line_shapes(draft.lines)
    async with session.begin_nested():
        entry = await _get_held(session, entry_id)
        for old in await _load_lines(session, entry_id):
            await session.delete(old)
        await session.flush()
        entry.date = draft.date
        entry.description = draft.description
        entry.source = draft.source
        entry.kind = draft.kind
        entry.invoice_id = draft.invoice_id
        entry.reverses_id = draft.reverses_id
        entry.note = draft.note
        _add_lines(session, entry.id, lines)
        _audit(
            session,
            "entry.revised",
            entry,
            actor or _DEFAULT_ACTOR[draft.source],
            {"date": draft.date.isoformat()},
        )
        await session.flush()
    return entry


async def reject_held(
    session: AsyncSession, entry_id: int, *, actor: AuditActor = AuditActor.BOSS
) -> JournalEntry:
    async with session.begin_nested():
        entry = await _get_held(session, entry_id)
        entry.status = EntryStatus.REJECTED
        _audit(session, "entry.rejected", entry, actor, {})
        await session.flush()
    return entry


async def post_held(
    session: AsyncSession,
    entry_id: int,
    *,
    source: EntrySource = EntrySource.BOSS_APPROVED,
    actor: AuditActor | None = None,
    now: dt.datetime | None = None,
) -> JournalEntry:
    async with session.begin_nested():
        entry = await _get_held(session, entry_id)
        rows = await _load_lines(session, entry_id)
        lines = check_lines([LineDraft(r.account_id, r.debit, r.credit, r.memo) for r in rows])
        return await _finalize(session, entry, lines, source=source, actor=actor, now=now)


async def reverse(
    session: AsyncSession,
    entry_id: int,
    *,
    source: EntrySource = EntrySource.MANUAL,
    date: dt.date | None = None,
    description: str | None = None,
    note: str | None = None,
    actor: AuditActor | None = None,
    now: dt.datetime | None = None,
) -> JournalEntry:
    async with session.begin_nested():
        original = await _get_for_update(session, entry_id)
        if original.status != EntryStatus.POSTED or original.entry_no is None:
            raise EntryStateError(f"Entry {entry_id} is not posted and cannot be reversed.")
        existing = await session.scalar(
            select(JournalEntry.id).where(
                JournalEntry.reverses_id == entry_id,
                JournalEntry.kind == EntryKind.REVERSAL,
                JournalEntry.status == EntryStatus.POSTED,
            )
        )
        if existing is not None:
            raise AlreadyReversedError(entry_id, existing)
        rows = await _load_lines(session, entry_id)
        label = format_entry_no(original.entry_no)
        draft = EntryDraft(
            date=date or original.date,
            description=description or f"Reversal of {label}: {original.description}",
            lines=[LineDraft(r.account_id, r.credit, r.debit, r.memo) for r in rows],
            source=source,
            kind=EntryKind.REVERSAL,
            invoice_id=original.invoice_id,
            reverses_id=original.id,
            note=note,
        )
        return await _post_new(session, draft, actor=actor, now=now)


async def correct(
    session: AsyncSession,
    entry_id: int,
    draft: EntryDraft,
    *,
    actor: AuditActor | None = None,
    now: dt.datetime | None = None,
) -> tuple[JournalEntry, JournalEntry]:
    if draft.kind == EntryKind.REVERSAL:
        raise InvalidEntryError("A correction's new entry cannot be a reversal.")
    if draft.reverses_id not in (None, entry_id):
        raise InvalidEntryError("A correction's new entry links to the entry it corrects.")
    _check_header(draft)
    check_lines(draft.lines)
    async with session.begin_nested():
        reversal = await reverse(session, entry_id, source=draft.source, actor=actor, now=now)
        new = await _post_new(session, replace(draft, reverses_id=entry_id), actor=actor, now=now)
    return reversal, new
