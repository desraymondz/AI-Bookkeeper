"""See planning/01-prd.md#f-013-deterministic-checks (F-013.3), planning/decisions.md#D-007."""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select

from bookkeeper.db.models import Account
from bookkeeper.ledger.checks.base import CheckContext, CheckResult
from bookkeeper.ledger.money import format_money

CODE = "gst"
GST_TOLERANCE = Decimal("0.05")
INPUT_GST_NAME = "Input GST"


async def _has_input_gst_line(ctx: CheckContext) -> bool:
    account_ids = await ctx.session.scalars(
        select(Account.id).where(Account.name == INPUT_GST_NAME)
    )
    gst_ids = set(account_ids.all())
    return any(line.account_id in gst_ids for line in ctx.proposed_entry.lines)


async def run(ctx: CheckContext) -> CheckResult:
    if not ctx.settings.gst_registered:
        if await _has_input_gst_line(ctx):
            return CheckResult(
                CODE, False, "Business is not GST registered but the entry claims Input GST."
            )
        return CheckResult(CODE, True, "Not GST registered; no Input GST claimed.")
    invoice = ctx.invoice
    if invoice.subtotal is None or invoice.gst is None:
        return CheckResult(CODE, False, "Subtotal or GST not read.")
    rate = ctx.settings.gst_rate
    expected = (invoice.subtotal * rate / Decimal(100)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    if abs(invoice.gst - expected) > GST_TOLERANCE:
        return CheckResult(
            CODE,
            False,
            f"GST should be {format_money(expected)} ({rate.normalize():f}% of "
            f"{format_money(invoice.subtotal)}), invoice says {format_money(invoice.gst)}.",
        )
    return CheckResult(
        CODE, True, f"GST {format_money(invoice.gst)} matches {rate.normalize():f}%."
    )
