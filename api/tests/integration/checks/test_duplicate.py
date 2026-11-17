"""T-113 to T-116, T-240. See planning/04-test-spec.md."""

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Document, EntrySource, JournalEntry
from bookkeeper.ledger import EntryDraft, LineDraft, hold_entry, reject_held
from bookkeeper.ledger.checks import duplicate
from bookkeeper.ledger.post import format_entry_no
from tests.integration.checks.support import add_document, add_invoice
from tests.support.factories import settings_row, supplier
from tests.unit.checks.builders import make_ctx, make_invoice, make_sender

pytestmark = pytest.mark.integration

TOTAL = Decimal("436.00")


async def test_t113_same_number_and_amounts_names_earlier_entry(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    settings = await settings_row(db_session)
    ocean = await supplier(db_session, "Ocean Fresh Pte Ltd", "5010")
    _, entry = await add_invoice(
        db_session,
        ocean,
        number="INV-1043",
        date=dt.date(2026, 11, 1),
        total=TOTAL,
        post_with=ids,
    )
    assert entry is not None
    assert entry.entry_no is not None
    doc = await add_document(db_session)
    ctx = make_ctx(
        db_session,
        settings=settings,
        supplier=ocean,
        sender=make_sender(ocean),
        invoice=make_invoice(invoice_date=dt.date(2026, 11, 2)),
        document=doc,
    )
    result = await duplicate.run(ctx)
    assert not result.passed
    assert format_entry_no(entry.entry_no) in result.detail


@pytest.mark.parametrize("has_current_invoice", [False, True])
async def test_t114_same_file_fails(
    db_session: AsyncSession, ids: dict[str, int], has_current_invoice: bool
) -> None:
    settings = await settings_row(db_session)
    ocean = await supplier(db_session, "Ocean Fresh Pte Ltd", "5010")
    earlier, _ = await add_invoice(
        db_session,
        ocean,
        number="INV-1043",
        date=dt.date(2026, 11, 1),
        total=TOTAL,
        post_with=ids,
    )
    doc = await db_session.get_one(Document, earlier.document_id)
    current_id = None
    if has_current_invoice:
        current, _ = await add_invoice(
            db_session,
            ocean,
            number="INV-9999",
            date=dt.date(2027, 6, 1),
            total=Decimal("1.00"),
            document=doc,
        )
        current_id = current.id
    ctx = make_ctx(
        db_session,
        settings=settings,
        supplier=ocean,
        sender=make_sender(ocean),
        invoice=make_invoice(invoice_no="INV-9999", total=Decimal("1.00")),
        document=doc,
        current_invoice_id=current_id,
    )
    result = await duplicate.run(ctx)
    assert not result.passed
    assert "INV-1043" in result.detail


async def test_only_match_is_current_invoice_passes(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    settings = await settings_row(db_session)
    ocean = await supplier(db_session, "Ocean Fresh Pte Ltd", "5010")
    current, _ = await add_invoice(
        db_session, ocean, number="INV-1043", date=dt.date(2026, 11, 1), total=TOTAL
    )
    doc = await db_session.get_one(Document, current.document_id)
    ctx = make_ctx(
        db_session,
        settings=settings,
        supplier=ocean,
        sender=make_sender(ocean),
        document=doc,
        current_invoice_id=current.id,
    )
    assert (await duplicate.run(ctx)).passed


async def test_rejected_earlier_invoice_is_not_a_duplicate(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    settings = await settings_row(db_session)
    ocean = await supplier(db_session, "Ocean Fresh Pte Ltd", "5010")
    earlier, _ = await add_invoice(
        db_session, ocean, number="INV-1043", date=dt.date(2026, 11, 1), total=TOTAL
    )
    await hold_entry(
        db_session,
        EntryDraft(
            date=dt.date(2026, 11, 1),
            description="Ocean Fresh INV-1043",
            lines=[
                LineDraft(ids["5010"], debit=TOTAL),
                LineDraft(ids["2000"], credit=TOTAL),
            ],
            source=EntrySource.AUTO,
            invoice_id=earlier.id,
        ),
    )
    entry_id = await db_session.scalar(
        select(JournalEntry.id).where(JournalEntry.invoice_id == earlier.id)
    )
    assert entry_id is not None
    ctx = make_ctx(
        db_session,
        settings=settings,
        supplier=ocean,
        sender=make_sender(ocean),
        document=await add_document(db_session),
    )
    assert not (await duplicate.run(ctx)).passed
    await reject_held(db_session, entry_id)
    assert (await duplicate.run(ctx)).passed


@pytest.mark.parametrize(("earlier_age_days", "passed"), [(30, False), (180, False), (200, True)])
async def test_t115_same_total_within_window(
    db_session: AsyncSession, ids: dict[str, int], earlier_age_days: int, passed: bool
) -> None:
    settings = await settings_row(db_session, dup_window_days=180)
    ocean = await supplier(db_session, "Ocean Fresh Pte Ltd", "5010")
    new_date = dt.date(2026, 11, 1)
    await add_invoice(
        db_session,
        ocean,
        number="INV-1000",
        date=new_date - dt.timedelta(days=earlier_age_days),
        total=TOTAL,
        post_with=ids,
    )
    ctx = make_ctx(
        db_session,
        settings=settings,
        supplier=ocean,
        sender=make_sender(ocean),
        invoice=make_invoice(invoice_no="INV-2000", invoice_date=new_date),
        document=await add_document(db_session),
    )
    assert (await duplicate.run(ctx)).passed is passed


async def test_t116_other_supplier_same_number_passes(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    settings = await settings_row(db_session)
    dairy = await supplier(db_session, "Dairy Best Pte Ltd", "5010")
    ocean = await supplier(db_session, "Ocean Fresh Pte Ltd", "5010")
    await add_invoice(
        db_session,
        dairy,
        number="INV-1043",
        date=dt.date(2026, 11, 1),
        total=TOTAL,
        post_with=ids,
    )
    ctx = make_ctx(
        db_session,
        settings=settings,
        supplier=ocean,
        sender=make_sender(ocean),
        invoice=make_invoice(total=Decimal("500.00"), subtotal=Decimal("458.72")),
        document=await add_document(db_session),
    )
    assert (await duplicate.run(ctx)).passed


@pytest.mark.parametrize(
    ("new_date", "passed"), [(dt.date(2027, 4, 30), False), (dt.date(2027, 5, 1), True)]
)
async def test_t240_window_measured_on_invoice_date(
    db_session: AsyncSession, ids: dict[str, int], new_date: dt.date, passed: bool
) -> None:
    settings = await settings_row(db_session, dup_window_days=180)
    ocean = await supplier(db_session, "Ocean Fresh Pte Ltd", "5010")
    await add_invoice(
        db_session,
        ocean,
        number="INV-1000",
        date=dt.date(2026, 11, 1),
        total=TOTAL,
        post_with=ids,
    )
    ctx = make_ctx(
        db_session,
        settings=settings,
        supplier=ocean,
        sender=make_sender(ocean),
        invoice=make_invoice(invoice_no="INV-2000", invoice_date=new_date),
        document=await add_document(db_session),
    )
    assert (await duplicate.run(ctx)).passed is passed
