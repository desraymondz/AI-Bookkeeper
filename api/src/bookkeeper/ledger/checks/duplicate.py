"""See planning/01-prd.md#f-013-deterministic-checks (F-013.5) and planning/decisions.md#D-024."""

import datetime as dt

from sqlalchemy import ColumnElement, select

from bookkeeper.db.models import Document, EntryKind, EntryStatus, Invoice, JournalEntry
from bookkeeper.ledger.checks.base import CheckContext, CheckResult
from bookkeeper.ledger.money import format_money
from bookkeeper.ledger.post import format_entry_no

CODE = "duplicate"


async def _earlier(ctx: CheckContext, invoice: Invoice) -> str:
    entry = await ctx.session.scalar(
        select(JournalEntry)
        .where(JournalEntry.invoice_id == invoice.id, JournalEntry.kind == EntryKind.NORMAL)
        .order_by(JournalEntry.id)
        .limit(1)
    )
    ref = invoice.invoice_no or f"invoice {invoice.id}"
    if entry is not None and entry.entry_no is not None:
        return f"{ref} ({format_entry_no(entry.entry_no)})"
    return ref


def _live() -> ColumnElement[bool]:
    any_entry = select(JournalEntry.id).where(JournalEntry.invoice_id == Invoice.id).exists()
    open_entry = (
        select(JournalEntry.id)
        .where(JournalEntry.invoice_id == Invoice.id, JournalEntry.status != EntryStatus.REJECTED)
        .exists()
    )
    return ~(any_entry & ~open_entry)


async def _first(ctx: CheckContext, *conditions: ColumnElement[bool]) -> Invoice | None:
    stmt = select(Invoice).where(*conditions, _live()).order_by(Invoice.id).limit(1)
    return await ctx.session.scalar(stmt)


async def run(ctx: CheckContext) -> CheckResult:
    document, invoice, supplier = ctx.document, ctx.invoice, ctx.supplier

    same_file_docs = select(Document.id).where(
        Document.sha256 == document.sha256, Document.id <= document.id
    )
    by_file = await _first(ctx, Invoice.document_id.in_(same_file_docs))
    if by_file is not None:
        return CheckResult(
            CODE, False, f"Same file already received as {await _earlier(ctx, by_file)}."
        )
    if supplier is None:
        return CheckResult(CODE, True, "No supplier to compare against.")

    others = (Invoice.supplier_id == supplier.id, Invoice.document_id != document.id)
    if invoice.invoice_no and invoice.total is not None:
        by_number = await _first(
            ctx,
            *others,
            Invoice.invoice_no == invoice.invoice_no,
            Invoice.total == invoice.total,
        )
        if by_number is not None:
            return CheckResult(
                CODE,
                False,
                f"{supplier.name} {invoice.invoice_no} already exists as "
                f"{await _earlier(ctx, by_number)} with the same total.",
            )
    if invoice.invoice_date is not None and invoice.total is not None:
        window = dt.timedelta(days=ctx.settings.dup_window_days)
        by_amount = await _first(
            ctx,
            *others,
            Invoice.total == invoice.total,
            Invoice.invoice_date >= invoice.invoice_date - window,
            Invoice.invoice_date <= invoice.invoice_date + window,
        )
        if by_amount is not None:
            return CheckResult(
                CODE,
                False,
                f"{supplier.name} already has {await _earlier(ctx, by_amount)} for "
                f"{format_money(invoice.total)} dated {by_amount.invoice_date} "
                f"(within {ctx.settings.dup_window_days} days).",
            )
    return CheckResult(CODE, True, "No earlier matching invoice or file.")
