"""See planning/04-test-spec.md T-104."""

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.agents.propose import propose_entry
from bookkeeper.agents.schemas import ExtractedInvoice
from bookkeeper.db.models import AuditLog
from tests.support.factories import seeded_chart, settings_row, supplier


async def test_t104_proposal_has_confidence_and_model_in_audit(db_session: AsyncSession) -> None:
    await seeded_chart(db_session)
    settings = await settings_row(db_session)
    sup = await supplier(db_session, "Ocean Fresh", "COGS Seafood")
    invoice = ExtractedInvoice(
        supplier_name="Ocean Fresh",
        invoice_no="INV-1043",
        invoice_date=dt.date(2026, 11, 10),
        due_date=None,
        terms_days=None,
        currency="SGD",
        lines=[],
        subtotal=Decimal("400.00"),
        gst=Decimal("36.00"),
        total=Decimal("436.00"),
        other_text=None,
        suspicious_content=False,
        confidence=Decimal("0.875"),
    )
    proposal = await propose_entry(
        db_session,
        invoice,
        supplier=sup,
        settings=settings,
        model="model-x",
        ref_type="document",
        ref_id=7,
    )
    assert proposal.confidence == Decimal("0.875")
    assert proposal.model == "model-x"
    row = await db_session.scalar(select(AuditLog).where(AuditLog.action == "invoice.proposed"))
    assert row is not None
    assert row.model == "model-x"
    assert row.detail_json["confidence"] == "0.875"
    assert (row.ref_type, row.ref_id) == ("document", "7")
