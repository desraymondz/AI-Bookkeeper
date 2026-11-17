"""See planning/01-prd.md#f-024-accounting-page-journal-tab-web."""

import datetime as dt
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Account,
    AuditActor,
    AuditLog,
    CheckResult,
    Document,
    EntryKind,
    EntrySource,
    EntryStatus,
    Invoice,
    JournalEntry,
    JournalLine,
)
from bookkeeper.ledger.post import format_entry_no
from bookkeeper.reports.balances import ZERO


class JournalLineOut(BaseModel):
    line_no: int
    account_id: int
    account_code: str
    account_name: str
    memo: str | None
    debit: Decimal
    credit: Decimal


class JournalEntryOut(BaseModel):
    id: int
    entry_no: str
    date: dt.date
    description: str
    source: EntrySource
    kind: EntryKind
    status: EntryStatus
    note: str | None
    lines: list[JournalLineOut]
    total_debit: Decimal
    total_credit: Decimal


class JournalListing(BaseModel):
    start: dt.date
    end: dt.date
    entries: list[JournalEntryOut]
    total_debit: Decimal
    total_credit: Decimal


class CheckOut(BaseModel):
    check_code: str
    passed: bool
    detail: str | None


class DocumentOut(BaseModel):
    document_id: int
    invoice_id: int
    mime: str
    kind: str


class AuditOut(BaseModel):
    at: dt.datetime
    actor: AuditActor
    action: str
    detail: dict[str, Any]


class LinkedEntry(BaseModel):
    id: int
    entry_no: str


class JournalEntryDetail(JournalEntryOut):
    checks: list[CheckOut]
    document: DocumentOut | None
    audit: list[AuditOut]
    reverses: LinkedEntry | None
    reversed_by: LinkedEntry | None


def _label(entry_no: int | None) -> str:
    return format_entry_no(entry_no) if entry_no is not None else ""


async def _lines_by_entry(
    session: AsyncSession, entry_ids: list[int]
) -> dict[int, list[JournalLineOut]]:
    stmt = (
        select(JournalLine, Account)
        .join(Account, Account.id == JournalLine.account_id)
        .where(JournalLine.entry_id.in_(entry_ids))
        .order_by(JournalLine.entry_id, JournalLine.line_no)
    )
    grouped: dict[int, list[JournalLineOut]] = {i: [] for i in entry_ids}
    for line, account in (await session.execute(stmt)).all():
        grouped[line.entry_id].append(
            JournalLineOut(
                line_no=line.line_no,
                account_id=account.id,
                account_code=account.code,
                account_name=account.name,
                memo=line.memo,
                debit=line.debit,
                credit=line.credit,
            )
        )
    return grouped


def _entry_out(entry: JournalEntry, lines: list[JournalLineOut]) -> JournalEntryOut:
    return JournalEntryOut(
        id=entry.id,
        entry_no=_label(entry.entry_no),
        date=entry.date,
        description=entry.description,
        source=entry.source,
        kind=entry.kind,
        status=entry.status,
        note=entry.note,
        lines=lines,
        total_debit=sum((ln.debit for ln in lines), ZERO),
        total_credit=sum((ln.credit for ln in lines), ZERO),
    )


async def journal_listing(
    session: AsyncSession,
    start: dt.date,
    end: dt.date,
    *,
    account_id: int | None = None,
) -> JournalListing:
    stmt = (
        select(JournalEntry)
        .where(
            JournalEntry.status == EntryStatus.POSTED,
            JournalEntry.date >= start,
            JournalEntry.date <= end,
        )
        .order_by(JournalEntry.date, JournalEntry.entry_no)
    )
    if account_id is not None:
        stmt = stmt.where(
            JournalEntry.id.in_(
                select(JournalLine.entry_id).where(JournalLine.account_id == account_id)
            )
        )
    entries = list((await session.execute(stmt)).scalars())
    lines = await _lines_by_entry(session, [e.id for e in entries])
    rows = [_entry_out(e, lines[e.id]) for e in entries]
    return JournalListing(
        start=start,
        end=end,
        entries=rows,
        total_debit=sum((r.total_debit for r in rows), ZERO),
        total_credit=sum((r.total_credit for r in rows), ZERO),
    )


async def journal_entry_detail(session: AsyncSession, entry_no: int) -> JournalEntryDetail | None:
    entry = await session.scalar(
        select(JournalEntry).where(
            JournalEntry.entry_no == entry_no, JournalEntry.status == EntryStatus.POSTED
        )
    )
    if entry is None:
        return None
    base = _entry_out(entry, (await _lines_by_entry(session, [entry.id]))[entry.id])
    checks = (
        await session.execute(
            select(CheckResult).where(CheckResult.entry_id == entry.id).order_by(CheckResult.id)
        )
    ).scalars()
    audit = (
        await session.execute(
            select(AuditLog)
            .where(AuditLog.ref_type == "journal_entry", AuditLog.ref_id == str(entry.id))
            .order_by(AuditLog.id)
        )
    ).scalars()
    document: DocumentOut | None = None
    if entry.invoice_id is not None:
        row = (
            await session.execute(
                select(Invoice, Document)
                .join(Document, Document.id == Invoice.document_id)
                .where(Invoice.id == entry.invoice_id)
            )
        ).first()
        if row is not None:
            invoice, doc = row
            document = DocumentOut(
                document_id=doc.id, invoice_id=invoice.id, mime=doc.mime, kind=doc.kind.value
            )
    reverses: LinkedEntry | None = None
    if entry.reverses_id is not None:
        original = await session.get(JournalEntry, entry.reverses_id)
        if original is not None:
            reverses = LinkedEntry(id=original.id, entry_no=_label(original.entry_no))
    reversal = await session.scalar(
        select(JournalEntry).where(
            JournalEntry.reverses_id == entry.id,
            JournalEntry.kind == EntryKind.REVERSAL,
            JournalEntry.status == EntryStatus.POSTED,
        )
    )
    reversed_by = (
        LinkedEntry(id=reversal.id, entry_no=_label(reversal.entry_no))
        if reversal is not None
        else None
    )
    return JournalEntryDetail(
        **base.model_dump(),
        checks=[
            CheckOut(check_code=c.check_code, passed=c.passed, detail=c.detail) for c in checks
        ],
        document=document,
        audit=[
            AuditOut(at=a.at, actor=a.actor, action=a.action, detail=a.detail_json) for a in audit
        ],
        reverses=reverses,
        reversed_by=reversed_by,
    )
