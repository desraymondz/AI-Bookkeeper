"""T-107 to T-109. See planning/04-test-spec.md."""

from decimal import Decimal

import pytest

from bookkeeper.agents.schemas import ExtractedLine
from bookkeeper.ledger.checks import arithmetic
from tests.unit.checks.builders import make_ctx, make_invoice


def _line(total: str) -> ExtractedLine:
    return ExtractedLine(
        description="Salmon",
        unit=None,
        qty=Decimal(10),
        unit_price=Decimal("28.00"),
        line_total=Decimal(total),
    )


@pytest.mark.parametrize(
    ("total", "passed"), [("280.00", True), ("280.01", True), ("279.99", True), ("280.02", False)]
)
async def test_t107_line_tolerance(total: str, passed: bool) -> None:
    invoice = make_invoice(
        lines=[_line(total)], subtotal=Decimal(total), gst=Decimal("0.00"), total=Decimal(total)
    )
    result = await arithmetic.run(make_ctx(invoice=invoice))
    assert result.passed is passed
    if not passed:
        assert "Line 1" in result.detail


async def test_t108_lines_not_summing_to_subtotal() -> None:
    invoice = make_invoice(
        subtotal=Decimal("410.00"), gst=Decimal("36.00"), total=Decimal("446.00")
    )
    result = await arithmetic.run(make_ctx(invoice=invoice))
    assert not result.passed
    assert "400.00" in result.detail
    assert "410.00" in result.detail


async def test_t109_total_not_subtotal_plus_gst() -> None:
    result = await arithmetic.run(make_ctx(invoice=make_invoice(total=Decimal("446.00"))))
    assert not result.passed
    assert "436.00" in result.detail


async def test_clean_invoice_passes() -> None:
    assert (await arithmetic.run(make_ctx())).passed


async def test_missing_total_fails() -> None:
    assert not (await arithmetic.run(make_ctx(invoice=make_invoice(total=None)))).passed
