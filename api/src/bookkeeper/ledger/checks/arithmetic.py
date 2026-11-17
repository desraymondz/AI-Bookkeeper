"""See planning/01-prd.md#f-013-deterministic-checks (F-013.2)."""

from decimal import Decimal

from bookkeeper.ledger.checks.base import CheckContext, CheckResult
from bookkeeper.ledger.money import ZERO, format_money

CODE = "arithmetic"
LINE_TOLERANCE = Decimal("0.01")


async def run(ctx: CheckContext) -> CheckResult:
    invoice = ctx.invoice
    problems: list[str] = []
    line_sum = ZERO
    for number, line in enumerate(invoice.lines, start=1):
        if line.line_total is None:
            problems.append(f"Line {number} has no line total.")
            continue
        line_sum += line.line_total
        if line.qty is None or line.unit_price is None:
            problems.append(f"Line {number} is missing quantity or unit price.")
            continue
        expected = (line.qty * line.unit_price).quantize(Decimal("0.01"))
        if abs(expected - line.line_total) > LINE_TOLERANCE:
            problems.append(
                f"Line {number}: {line.qty} x {format_money(line.unit_price)} is "
                f"{format_money(expected)}, invoice says {format_money(line.line_total)}."
            )
    if not invoice.lines:
        problems.append("Invoice has no line items.")
    if invoice.subtotal is None or invoice.total is None:
        problems.append("Subtotal or total not read.")
    else:
        if invoice.lines and line_sum != invoice.subtotal:
            problems.append(
                f"Sum of lines is {format_money(line_sum)} but subtotal is "
                f"{format_money(invoice.subtotal)}."
            )
        expected_total = invoice.subtotal + (invoice.gst or ZERO)
        if expected_total != invoice.total:
            problems.append(
                f"Subtotal plus GST should be {format_money(expected_total)}, "
                f"invoice total is {format_money(invoice.total)}."
            )
    if problems:
        return CheckResult(CODE, False, " ".join(problems))
    return CheckResult(CODE, True, "Lines, subtotal and total add up.")
