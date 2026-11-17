"""See planning/04-test-spec.md T-122 to T-124."""

import datetime as dt
from decimal import Decimal

import pytest
import time_machine

from bookkeeper.ledger.checks import sanity
from tests.unit.checks.ctx_stub import StubInvoice, make_ctx

NOW = dt.datetime(2026, 11, 18, 3, 0, tzinfo=dt.UTC)


@time_machine.travel(NOW, tick=False)
async def test_t122_future_date_fails() -> None:
    result = await sanity.run(make_ctx(StubInvoice(invoice_date=dt.date(2026, 11, 19))))
    assert not result.passed
    assert result.detail is not None
    assert "future" in result.detail


@time_machine.travel(NOW, tick=False)
async def test_today_passes() -> None:
    result = await sanity.run(make_ctx(StubInvoice(invoice_date=dt.date(2026, 11, 18))))
    assert result.passed


@time_machine.travel(NOW, tick=False)
async def test_t123_older_than_twelve_months_fails() -> None:
    result = await sanity.run(make_ctx(StubInvoice(invoice_date=dt.date(2025, 11, 17))))
    assert not result.passed
    assert result.detail is not None
    assert "12 months" in result.detail


@time_machine.travel(NOW, tick=False)
async def test_exactly_twelve_months_passes() -> None:
    result = await sanity.run(make_ctx(StubInvoice(invoice_date=dt.date(2025, 11, 18))))
    assert result.passed


@time_machine.travel(NOW, tick=False)
async def test_business_timezone_decides_today() -> None:
    late_utc = dt.datetime(2026, 11, 18, 18, 0, tzinfo=dt.UTC)
    with time_machine.travel(late_utc, tick=False):
        result = await sanity.run(make_ctx(StubInvoice(invoice_date=dt.date(2026, 11, 19))))
    assert result.passed


@time_machine.travel(NOW, tick=False)
@pytest.mark.parametrize(
    ("total", "currency"),
    [(Decimal("0.00"), "SGD"), (Decimal("-5.00"), "SGD"), (None, "SGD"), (Decimal("10.00"), "USD")],
)
async def test_t124_zero_total_or_wrong_currency_fails(
    total: Decimal | None, currency: str
) -> None:
    result = await sanity.run(make_ctx(StubInvoice(total=total, currency=currency)))
    assert not result.passed


@time_machine.travel(NOW, tick=False)
async def test_clean_invoice_passes() -> None:
    result = await sanity.run(make_ctx(StubInvoice()))
    assert result.passed
    assert result.code == "F-013.9"
