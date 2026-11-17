"""See planning/01-prd.md#f-013-deterministic-checks (F-013.8) and planning/decisions.md#D-024."""

from bookkeeper.ledger.checks.base import CheckContext, CheckResult
from bookkeeper.ledger.periods import format_day, is_locked

CODE = "F-013.8"


async def run(ctx: CheckContext) -> CheckResult:
    invoice_date = ctx.invoice.invoice_date
    if invoice_date is None:
        return CheckResult(CODE, True, None)
    if await is_locked(ctx.session, invoice_date):
        return CheckResult(
            CODE,
            False,
            f"Invoice date {format_day(invoice_date)} is in locked period {invoice_date:%b %Y}",
        )
    return CheckResult(CODE, True, None)
