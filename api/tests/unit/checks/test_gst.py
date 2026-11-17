"""T-110. See planning/04-test-spec.md."""

from decimal import Decimal

import pytest

from bookkeeper.ledger.checks import gst
from tests.unit.checks.builders import make_ctx, make_invoice


@pytest.mark.parametrize(
    ("amount", "passed"), [("36.00", True), ("36.05", True), ("36.06", False), ("40.00", False)]
)
async def test_t110_registered_tolerance(amount: str, passed: bool) -> None:
    result = await gst.run(make_ctx(invoice=make_invoice(gst=Decimal(amount))))
    assert result.passed is passed
    if not passed:
        assert "36.00" in result.detail


async def test_registered_missing_gst_fails() -> None:
    assert not (await gst.run(make_ctx(invoice=make_invoice(gst=None)))).passed
