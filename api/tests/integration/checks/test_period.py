"""See planning/04-test-spec.md T-121."""

import datetime as dt

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.ledger import lock_period
from bookkeeper.ledger.checks import period
from tests.unit.checks.builders import make_ctx, make_invoice

pytestmark = pytest.mark.integration


async def test_t121_locked_period_fails_open_period_passes(db_session: AsyncSession) -> None:
    await lock_period(db_session, 2026, 10)

    locked = await period.run(
        make_ctx(db_session, invoice=make_invoice(invoice_date=dt.date(2026, 10, 15)))
    )
    open_ = await period.run(
        make_ctx(db_session, invoice=make_invoice(invoice_date=dt.date(2026, 11, 2)))
    )

    assert not locked.passed
    assert "Oct 2026" in locked.detail
    assert open_.passed
    assert open_.code == "period"
