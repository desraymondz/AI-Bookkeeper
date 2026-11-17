"""See planning/04-test-spec.md T-121."""

import datetime as dt

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.ledger import lock_period
from bookkeeper.ledger.checks import period
from tests.support.factories import settings_row
from tests.unit.checks.ctx_stub import StubInvoice, make_ctx

pytestmark = pytest.mark.integration


async def test_t121_locked_period_fails_open_period_passes(db_session: AsyncSession) -> None:
    settings = await settings_row(db_session)
    await lock_period(db_session, 2026, 10)

    locked = await period.run(
        make_ctx(
            StubInvoice(invoice_date=dt.date(2026, 10, 15)), session=db_session, settings=settings
        )
    )
    open_ = await period.run(
        make_ctx(
            StubInvoice(invoice_date=dt.date(2026, 11, 2)), session=db_session, settings=settings
        )
    )

    assert not locked.passed
    assert locked.detail is not None
    assert "Oct 2026" in locked.detail
    assert open_.passed
    assert open_.code == "F-013.8"
