"""See planning/04-test-spec.md T-117 and T-239."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.ledger.checks import revision
from tests.integration.checks.rows import add_document, add_invoice
from tests.support.factories import settings_row, supplier
from tests.unit.checks.ctx_stub import StubInvoice, StubLine, make_ctx

pytestmark = pytest.mark.integration

ORIGINAL = [StubLine("Salmon Fillet", Decimal("20"), "kg", Decimal("11.80"), Decimal("236.00"))]


async def seed(session: AsyncSession) -> tuple[object, object]:
    await settings_row(session)
    ocean = await supplier(session, "Ocean Fresh", "5000")
    await add_invoice(
        session,
        ocean,
        "INV-1043",
        ORIGINAL,
        subtotal=Decimal("400.00"),
        gst=Decimal("36.00"),
        total=Decimal("436.00"),
    )
    return ocean, await add_document(session)


@pytest.mark.usefixtures("ids")
async def test_t117_extra_line_and_new_total_is_revision(db_session: AsyncSession) -> None:
    ocean, document = await seed(db_session)
    invoice = StubInvoice(
        subtotal=Decimal("432.00"),
        gst=Decimal("38.88"),
        total=Decimal("470.88"),
        lines=[
            *ORIGINAL,
            StubLine("Squid", Decimal("5"), "kg", Decimal("39.20"), Decimal("196.00")),
        ],
    )
    result = await revision.run(
        make_ctx(invoice, session=db_session, supplier=ocean, document=document)
    )
    assert not result.passed
    assert result.code == "F-013.6"


@pytest.mark.usefixtures("ids")
async def test_t239_changed_total_is_revision(db_session: AsyncSession) -> None:
    ocean, document = await seed(db_session)
    invoice = StubInvoice(
        subtotal=Decimal("420.00"), gst=Decimal("37.80"), total=Decimal("457.80"), lines=ORIGINAL
    )
    result = await revision.run(
        make_ctx(invoice, session=db_session, supplier=ocean, document=document)
    )
    assert not result.passed


@pytest.mark.usefixtures("ids")
async def test_identical_resend_is_not_revision(db_session: AsyncSession) -> None:
    ocean, document = await seed(db_session)
    invoice = StubInvoice(lines=ORIGINAL)
    result = await revision.run(
        make_ctx(invoice, session=db_session, supplier=ocean, document=document)
    )
    assert result.passed


@pytest.mark.usefixtures("ids")
async def test_other_supplier_or_number_passes(db_session: AsyncSession) -> None:
    ocean, document = await seed(db_session)
    other = await supplier(db_session, "Green Farm", "5000")
    changed = StubInvoice(total=Decimal("999.00"), lines=ORIGINAL)
    for ctx in (
        make_ctx(changed, session=db_session, supplier=other, document=document),
        make_ctx(
            StubInvoice(invoice_no="INV-2000", total=Decimal("999.00"), lines=ORIGINAL),
            session=db_session,
            supplier=ocean,
            document=document,
        ),
    ):
        assert (await revision.run(ctx)).passed
