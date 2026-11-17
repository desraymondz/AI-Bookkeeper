"""See planning/01-prd.md#f-013-deterministic-checks (F-013.7) and planning/decisions.md#D-029."""

from decimal import Decimal

from sqlalchemy import select

from bookkeeper.db.models import EntryStatus, Invoice, InvoiceLine, JournalEntry
from bookkeeper.ledger.checks.base import CheckContext, CheckResult

CODE = "price_change"
INCREASE_ONLY = "increase_only"


def _fmt(value: Decimal) -> str:
    return f"{value:,.2f}"


def normalize_item(value: str | None) -> str:
    return " ".join((value or "").lower().split())


async def _last_prices(ctx: CheckContext, supplier_id: int) -> dict[str, Decimal]:
    rows = await ctx.session.execute(
        select(InvoiceLine.normalized_item, InvoiceLine.description, InvoiceLine.unit_price)
        .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
        .join(JournalEntry, JournalEntry.invoice_id == Invoice.id)
        .where(
            Invoice.supplier_id == supplier_id,
            Invoice.document_id != ctx.document.id,
            Invoice.id != (ctx.current_invoice_id or 0),
            JournalEntry.status == EntryStatus.POSTED,
            InvoiceLine.unit_price.is_not(None),
        )
        .order_by(
            Invoice.invoice_date.desc().nulls_last(), Invoice.id.desc(), InvoiceLine.line_no.desc()
        )
    )
    last: dict[str, Decimal] = {}
    for normalized, description, unit_price in rows.all():
        key = normalize_item(normalized or description)
        if key and key not in last and unit_price is not None:
            last[key] = unit_price
    return last


async def run(ctx: CheckContext) -> CheckResult:
    lines = [line for line in ctx.invoice.lines if line.unit_price is not None]
    if not lines or ctx.supplier is None:
        return CheckResult(CODE, True, "No unit prices to compare.")
    last = await _last_prices(ctx, ctx.supplier.id)
    increase_only = ctx.settings.price_rule == INCREASE_ONLY

    findings: list[tuple[str, str]] = []
    for line in lines:
        key = normalize_item(line.description)
        previous = last.get(key)
        if line.unit_price is None or previous is None or line.unit_price == previous:
            continue
        if increase_only and line.unit_price < previous:
            continue
        findings.append(
            (
                (line.description or "").strip(),
                f"Unit price {_fmt(line.unit_price)}, last {_fmt(previous)}",
            )
        )

    if not findings:
        return CheckResult(CODE, True, "No price differs from the last invoice.")
    if len(findings) == 1:
        return CheckResult(CODE, False, findings[0][1])
    return CheckResult(CODE, False, "; ".join(f"{name}: {text}" for name, text in findings))
