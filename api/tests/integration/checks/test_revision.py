"""See planning/04-test-spec.md T-117 and T-239."""

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.agents.schemas import ExtractedLine
from bookkeeper.db.models import Invoice, Supplier
from bookkeeper.ledger.checks import revision
from tests.integration.checks.lines import add_lines
from tests.integration.checks.support import add_document, add_invoice
from tests.support.factories import supplier
from tests.unit.checks.builders import make_ctx, make_invoice

pytestmark = pytest.mark.integration

D = Decimal
SALMON = ExtractedLine(
    description="Salmon Fillet",
    qty=D("20"),
    unit="kg",
    unit_price=D("11.80"),
    line_total=D("236.00"),
)
SQUID = ExtractedLine(
    description="Squid", qty=D("5"), unit="kg", unit_price=D("39.20"), line_total=D("196.00")
)


async def seed(session: AsyncSession) -> tuple[Supplier, Invoice]:
    ocean = await supplier(session, "Ocean Fresh Pte Ltd", "5010")
    original, _ = await add_invoice(
        session, ocean, number="INV-1043", date=dt.date(2026, 10, 20), total=D("436.00")
    )
    await add_lines(session, original, [SALMON], subtotal=D("400.00"), gst=D("36.00"))
    return ocean, original


@pytest.mark.usefixtures("ids")
async def test_t117_extra_line_and_new_total_is_revision(db_session: AsyncSession) -> None:
    ocean, _ = await seed(db_session)
    invoice = make_invoice(
        subtotal=D("432.00"), gst=D("38.88"), total=D("470.88"), lines=[SALMON, SQUID]
    )
    document = await add_document(db_session)
    result = await revision.run(
        make_ctx(db_session, invoice=invoice, supplier=ocean, document=document)
    )
    assert not result.passed
    assert result.code == "revision"


@pytest.mark.usefixtures("ids")
async def test_t239_changed_total_is_revision(db_session: AsyncSession) -> None:
    ocean, _ = await seed(db_session)
    invoice = make_invoice(subtotal=D("420.00"), gst=D("37.80"), total=D("457.80"), lines=[SALMON])
    result = await revision.run(
        make_ctx(
            db_session, invoice=invoice, supplier=ocean, document=await add_document(db_session)
        )
    )
    assert not result.passed


@pytest.mark.usefixtures("ids")
async def test_identical_resend_is_not_revision(db_session: AsyncSession) -> None:
    ocean, _ = await seed(db_session)
    result = await revision.run(
        make_ctx(
            db_session,
            invoice=make_invoice(lines=[SALMON]),
            supplier=ocean,
            document=await add_document(db_session),
        )
    )
    assert result.passed


@pytest.mark.usefixtures("ids")
async def test_current_invoice_row_is_excluded(db_session: AsyncSession) -> None:
    ocean, original = await seed(db_session)
    result = await revision.run(
        make_ctx(
            db_session,
            invoice=make_invoice(total=D("999.00"), lines=[SALMON]),
            supplier=ocean,
            document=await add_document(db_session),
            current_invoice_id=original.id,
        )
    )
    assert result.passed


@pytest.mark.usefixtures("ids")
async def test_other_supplier_or_number_passes(db_session: AsyncSession) -> None:
    ocean, _ = await seed(db_session)
    other = await supplier(db_session, "Green Farm", "5010")
    document = await add_document(db_session)
    changed = make_invoice(total=D("999.00"), lines=[SALMON])
    renumbered = make_invoice(invoice_no="INV-2000", total=D("999.00"), lines=[SALMON])
    for ctx in (
        make_ctx(db_session, invoice=changed, supplier=other, document=document),
        make_ctx(db_session, invoice=renumbered, supplier=ocean, document=document),
    ):
        assert (await revision.run(ctx)).passed
