"""See planning/01-prd.md#global-rules (G-1) and F-013.4."""

from bookkeeper.ledger.checks.base import CheckContext, CheckResult
from bookkeeper.ledger.money import ZERO, format_money

CODE = "balanced"


async def run(ctx: CheckContext) -> CheckResult:
    lines = ctx.proposed_entry.lines
    debits = sum((line.debit for line in lines), ZERO)
    credits = sum((line.credit for line in lines), ZERO)
    if debits != credits:
        return CheckResult(
            CODE,
            False,
            f"Debits {format_money(debits)} and credits {format_money(credits)} "
            f"differ by {format_money(abs(debits - credits))}.",
        )
    if len(lines) < 2:
        return CheckResult(CODE, False, "Entry needs at least two lines.")
    return CheckResult(CODE, True, f"Debits and credits both {format_money(debits)}.")
