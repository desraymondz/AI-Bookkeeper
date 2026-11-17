"""See planning/04-test-spec.md T-118 to T-120 and planning/decisions.md#D-029."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import BusinessSettings, Supplier
from bookkeeper.ledger.checks import CheckResult, price_change
from tests.integration.checks.rows import add_document, add_invoice
from tests.support.factories import settings_row, supplier
from tests.unit.checks.ctx_stub import StubInvoice, StubLine, make_ctx

pytestmark = pytest.mark.integration


def salmon(price: str, description: str = "Salmon Fillet ") -> StubLine:
    return StubLine(description, Decimal("10"), "kg", Decimal(price), Decimal(price) * 10)


async def seed(session: AsyncSession, **settings: str) -> tuple[BusinessSettings, Supplier]:
    row = await settings_row(session, **settings)
    ocean = await supplier(session, "Ocean Fresh", "5000")
    await add_invoice(
        session,
        ocean,
        "INV-1000",
        [salmon("11.80", "salmon fillet")],
        subtotal=Decimal("118.00"),
        gst=Decimal("10.62"),
        total=Decimal("128.62"),
    )
    return row, ocean


async def check(
    session: AsyncSession, row: BusinessSettings, ocean: Supplier, lines: list[StubLine]
) -> CheckResult:
    document = await add_document(session)
    return await price_change.run(
        make_ctx(
            StubInvoice(invoice_no="INV-2000", lines=lines),
            session=session,
            settings=row,
            supplier=ocean,
            document=document,
        )
    )


@pytest.mark.usefixtures("ids")
async def test_t118_changed_price_fails_with_detail(db_session: AsyncSession) -> None:
    row, ocean = await seed(db_session)
    result = await check(db_session, row, ocean, [salmon("12.40")])
    assert not result.passed
    assert result.detail == "Unit price 12.40, last 11.80"
    assert result.code == "F-013.7"


@pytest.mark.usefixtures("ids")
async def test_t119_normalized_match_same_price_passes(db_session: AsyncSession) -> None:
    row, ocean = await seed(db_session)
    result = await check(db_session, row, ocean, [salmon("11.80", "SALMON  FILLET")])
    assert result.passed


@pytest.mark.usefixtures("ids")
async def test_t120_new_item_or_other_supplier_passes(db_session: AsyncSession) -> None:
    row, ocean = await seed(db_session)
    other = await supplier(db_session, "Green Farm", "5000")
    new_item = await check(db_session, row, ocean, [salmon("5.00", "Squid")])
    other_supplier = await check(db_session, row, other, [salmon("20.00")])
    assert new_item.passed
    assert other_supplier.passed


@pytest.mark.usefixtures("ids")
async def test_increase_only_rule_ignores_decreases(db_session: AsyncSession) -> None:
    row, ocean = await seed(db_session, price_rule="increase_only")
    lower = await check(db_session, row, ocean, [salmon("10.00")])
    higher = await check(db_session, row, ocean, [salmon("12.00")])
    assert lower.passed
    assert not higher.passed


@pytest.mark.usefixtures("ids")
async def test_any_change_rule_flags_decreases(db_session: AsyncSession) -> None:
    row, ocean = await seed(db_session)
    lower = await check(db_session, row, ocean, [salmon("10.00")])
    assert not lower.passed
    assert lower.detail == "Unit price 10.00, last 11.80"


@pytest.mark.usefixtures("ids")
async def test_unposted_invoice_is_not_a_baseline(db_session: AsyncSession) -> None:
    row = await settings_row(db_session)
    ocean = await supplier(db_session, "Ocean Fresh", "5000")
    await add_invoice(
        db_session,
        ocean,
        "INV-1000",
        [salmon("11.80")],
        subtotal=Decimal("118.00"),
        gst=Decimal("10.62"),
        total=Decimal("128.62"),
        posted=False,
    )
    assert (await check(db_session, row, ocean, [salmon("15.00")])).passed
