"""T-112. See planning/04-test-spec.md."""

from decimal import Decimal

from bookkeeper.ledger.checks import balanced
from tests.unit.checks.builders import make_ctx, make_entry


async def test_t112_unbalanced_fails_with_difference() -> None:
    result = await balanced.run(make_ctx(entry=make_entry(ap=Decimal("435.00"))))
    assert not result.passed
    assert "1.00" in result.detail


async def test_balanced_passes() -> None:
    assert (await balanced.run(make_ctx())).passed
