"""T-111, T-125, T-036 (second half). See planning/04-test-spec.md."""

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import BusinessSettings
from bookkeeper.db.models import CheckResult as CheckRow
from bookkeeper.ledger.checks import CHECKS, gst, run_checks, store_results
from bookkeeper.settings_service import SettingsInput, save_settings
from tests.integration.checks.support import add_document
from tests.support.factories import post, settings_row, supplier
from tests.unit.checks.builders import make_ctx, make_entry, make_invoice, make_sender

pytestmark = pytest.mark.integration


async def test_t111_unregistered_with_input_gst_line_fails(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    settings = await settings_row(db_session, gst_registered=False)
    entry = make_entry(gst_account=ids["1200"])
    result = await gst.run(make_ctx(db_session, settings=settings, entry=entry))
    assert not result.passed


async def test_unregistered_without_input_gst_line_passes(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    settings = await settings_row(db_session, gst_registered=False)
    entry = make_entry(debit_gst=None)
    assert (await gst.run(make_ctx(db_session, settings=settings, entry=entry))).passed


async def test_t036_rate_change_applies_to_next_invoice(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    await settings_row(db_session, gst_rate="9.00")
    posted = await post(
        db_session,
        dt.date(2026, 11, 1),
        [("5010", "400.00", "0"), ("1200", "36.00", "0"), ("2000", "0", "436.00")],
    )
    saved = await save_settings(
        db_session, SettingsInput(name="Kopi Corner", gst_registered=True, gst_rate="8.00")
    )
    assert saved.gst_rate == Decimal("8.00")
    settings = (await db_session.scalars(select(BusinessSettings))).one()
    await db_session.refresh(settings)

    at_nine = await gst.run(make_ctx(db_session, settings=settings, invoice=make_invoice()))
    at_eight = await gst.run(
        make_ctx(db_session, settings=settings, invoice=make_invoice(gst=Decimal("32.00")))
    )
    assert not at_nine.passed
    assert "32.00" in at_nine.detail
    assert at_eight.passed
    assert posted.id is not None


async def test_t125_every_check_stores_result_with_reason(
    db_session: AsyncSession, ids: dict[str, int]
) -> None:
    settings = await settings_row(db_session)
    ocean = await supplier(db_session, "Ocean Fresh Pte Ltd", "5010")
    entry = await post(
        db_session,
        dt.date(2026, 11, 1),
        [("5010", "400.00", "0"), ("1200", "36.00", "0"), ("2000", "0", "436.00")],
    )
    ctx = make_ctx(
        db_session,
        settings=settings,
        supplier=ocean,
        sender=make_sender(ocean),
        entry=make_entry(gst_account=ids["1200"]),
        document=await add_document(db_session),
    )
    results = await run_checks(ctx)
    assert len(results) == len(CHECKS)
    assert len({r.code for r in results}) == len(CHECKS)
    assert {"known_supplier", "arithmetic", "gst", "balanced", "duplicate"} <= {
        r.code for r in results
    }
    assert all(r.detail.strip() for r in results)

    await store_results(db_session, entry.id, results)
    rows = (await db_session.scalars(select(CheckRow).where(CheckRow.entry_id == entry.id))).all()
    assert {r.check_code for r in rows} == {r.code for r in results}
    assert all(r.detail for r in rows)
