"""See planning/01-prd.md#f-013-deterministic-checks (F-013.9)."""

import datetime as dt
from zoneinfo import ZoneInfo

from bookkeeper.ledger.checks.base import CheckContext, CheckResult
from bookkeeper.ledger.periods import format_day

CODE = "sanity"
MAX_AGE_MONTHS = 12


def _years_back(day: dt.date, years: int) -> dt.date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


async def run(ctx: CheckContext) -> CheckResult:
    today = dt.datetime.now(dt.UTC).astimezone(ZoneInfo(ctx.settings.timezone)).date()
    problems: list[str] = []

    invoice_date = ctx.invoice.invoice_date
    if invoice_date is None:
        problems.append("Invoice date is missing")
    elif invoice_date > today:
        problems.append(f"Invoice date {format_day(invoice_date)} is in the future")
    elif invoice_date < _years_back(today, 1):
        problems.append(f"Invoice date {format_day(invoice_date)} is older than 12 months")

    total = ctx.invoice.total
    if total is None or total <= 0:
        problems.append(f"Total {total if total is not None else 'missing'} is not above zero")

    currency = ctx.invoice.currency
    business = ctx.settings.currency.upper()
    if currency is None or currency.strip().upper() != business:
        problems.append(f"Currency {currency or 'missing'} is not {business}")

    return CheckResult(
        CODE, not problems, "; ".join(problems) or "Date, total and currency are sane."
    )
