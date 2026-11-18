"""See planning/01-prd.md#f-013-deterministic-checks (F-013.6)."""

from collections import Counter
from decimal import Decimal

from sqlalchemy import func, select

from bookkeeper.db.models import Invoice, InvoiceLine
from bookkeeper.ledger.checks.base import CheckContext, CheckResult

CODE = "revision"


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def _amount(value: Decimal | None) -> Decimal | None:
    return None if value is None else value.normalize()


LineKey = tuple[str, Decimal | None, Decimal | None, Decimal | None]


def _line_key(
    description: str | None,
    qty: Decimal | None,
    unit_price: Decimal | None,
    line_total: Decimal | None,
) -> LineKey:
    return (normalize_text(description), _amount(qty), _amount(unit_price), _amount(line_total))


async def run(ctx: CheckContext) -> CheckResult:
    invoice = ctx.invoice
    if not invoice.invoice_no or ctx.supplier is None:
        return CheckResult(CODE, True, "No invoice number or supplier to compare.")

    prior = (
        await ctx.session.scalars(
            select(Invoice)
            .where(
                Invoice.supplier_id == ctx.supplier.id,
                func.lower(func.btrim(Invoice.invoice_no)) == normalize_text(invoice.invoice_no),
                Invoice.document_id != ctx.document.id,
                Invoice.id != (ctx.current_invoice_id or 0),
            )
            .order_by(Invoice.id.desc())
        )
    ).all()
    if not prior:
        return CheckResult(CODE, True, "Invoice number not seen before.")

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
            return CheckResult(CODE, True, "Matches the earlier copy exactly.")

    latest = prior[0]
    return CheckResult(
        CODE,
        False,
        f"Revised invoice: {invoice.invoice_no} was received before with total "
        f"{latest.total} and now has total {invoice.total}",
    )
