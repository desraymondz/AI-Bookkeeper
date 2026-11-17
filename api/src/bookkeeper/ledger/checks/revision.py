"""See planning/01-prd.md#f-013-deterministic-checks (F-013.6)."""

from collections import Counter
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from bookkeeper.db.models import Invoice, InvoiceLine
from bookkeeper.ledger.checks.base import CheckContext, CheckResult

CODE = "F-013.6"


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def _amount(value: Decimal | None) -> Decimal | None:
    return None if value is None else value.normalize()


LineKey = tuple[str, Decimal | None, Decimal | None, Decimal | None]


def _line_key(description: str | None, qty: Any, unit_price: Any, line_total: Any) -> LineKey:
    return (normalize_text(description), _amount(qty), _amount(unit_price), _amount(line_total))


async def run(ctx: CheckContext) -> CheckResult:
    invoice = ctx.invoice
    if not invoice.invoice_no:
        return CheckResult(CODE, True, None)

    prior = (
        await ctx.session.scalars(
            select(Invoice)
            .where(
                Invoice.supplier_id == ctx.supplier.id,
                func.lower(func.btrim(Invoice.invoice_no)) == normalize_text(invoice.invoice_no),
                Invoice.document_id != ctx.document.id,
            )
            .order_by(Invoice.id.desc())
        )
    ).all()
    if not prior:
        return CheckResult(CODE, True, None)

    current_lines = Counter(
        _line_key(line.description, line.qty, line.unit_price, line.line_total)
        for line in invoice.lines
    )
    for earlier in prior:
        rows = (
            await ctx.session.scalars(
                select(InvoiceLine).where(InvoiceLine.invoice_id == earlier.id)
            )
        ).all()
        earlier_lines = Counter(
            _line_key(row.description, row.qty, row.unit_price, row.line_total) for row in rows
        )
        same_amounts = (
            _amount(earlier.subtotal) == _amount(invoice.subtotal)
            and _amount(earlier.gst) == _amount(invoice.gst)
            and _amount(earlier.total) == _amount(invoice.total)
        )
        if same_amounts and earlier_lines == current_lines:
            return CheckResult(CODE, True, None)

    latest = prior[0]
    return CheckResult(
        CODE,
        False,
        f"Revised invoice: {invoice.invoice_no} was received before with total "
        f"{latest.total} and now has total {invoice.total}",
    )
