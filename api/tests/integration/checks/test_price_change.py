"""See planning/04-test-spec.md T-118 to T-120 and planning/decisions.md#D-029."""

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.agents.schemas import ExtractedLine
from bookkeeper.db.models import BusinessSettings, Supplier
from bookkeeper.ledger.checks import CheckResult, price_change
from tests.integration.checks.lines import add_lines
from tests.integration.checks.support import add_document, add_invoice
from tests.support.factories import settings_row, supplier
from tests.unit.checks.builders import make_ctx, make_invoice

pytestmark = pytest.mark.integration


def salmon(price: str, description: str = "Salmon Fillet ") -> ExtractedLine:
    return ExtractedLine(
        description=description,
        qty=Decimal("10"),
        unit="kg",
        unit_price=Decimal(price),
        line_total=Decimal(price) * 10,
    )


async def seed(
    session: AsyncSession, ids: dict[str, int], *, posted: bool = True, **settings: str
) -> tuple[BusinessSettings, Supplier]:
    row = await settings_row(session, **settings)
    ocean = await supplier(session, "Ocean Fresh Pte Ltd", "5010")
    invoice, _ = await add_invoice(
        session,
        ocean,
        number="INV-1000",
        date=dt.date(2026, 10, 20),
        total=Decimal("118.00"),
        post_with=ids if posted else None,
    )
    await add_lines(
        session,
        invoice,
        [salmon("11.80", "salmon fillet")],
        subtotal=Decimal("118.00"),
        gst=Decimal(0),
    )
    return row, ocean


async def check(
    session: AsyncSession, row: BusinessSettings, ocean: Supplier, lines: list[ExtractedLine]
) -> CheckResult:
    return await price_change.run(
        make_ctx(
            session,
            invoice=make_invoice(invoice_no="INV-2000", lines=lines),
            settings=row,
            supplier=ocean,
            document=await add_document(session),
        )
    )


async def test_t118_changed_price_fails_with_detail(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    row, ocean = await seed(db_session, ids)
    result = await check(db_session, row, ocean, [salmon("12.40")])
    assert not result.passed
    assert result.detail == "Unit price 12.40, last 11.80"
    assert result.code == "price_change"


async def test_t119_normalized_match_same_price_passes(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    row, ocean = await seed(db_session, ids)
    assert (await check(db_session, row, ocean, [salmon("11.80", "SALMON  FILLET")])).passed


async def test_t120_new_item_or_other_supplier_passes(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    row, ocean = await seed(db_session, ids)
    other = await supplier(db_session, "Green Farm", "5010")
    assert (await check(db_session, row, ocean, [salmon("5.00", "Squid")])).passed
    assert (await check(db_session, row, other, [salmon("20.00")])).passed


async def test_increase_only_rule_ignores_decreases(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    row, ocean = await seed(db_session, ids, price_rule="increase_only")
    assert (await check(db_session, row, ocean, [salmon("10.00")])).passed
    assert not (await check(db_session, row, ocean, [salmon("12.00")])).passed


async def test_any_change_rule_flags_decreases(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    row, ocean = await seed(db_session, ids)
    lower = await check(db_session, row, ocean, [salmon("10.00")])
    assert not lower.passed
    assert lower.detail == "Unit price 10.00, last 11.80"


async def test_unposted_invoice_is_not_a_baseline(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    row, ocean = await seed(db_session, ids, posted=False)
    assert (await check(db_session, row, ocean, [salmon("15.00")])).passed
