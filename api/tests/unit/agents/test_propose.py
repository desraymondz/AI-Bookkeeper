"""See planning/04-test-spec.md T-102, T-103, T-044."""

import datetime as dt
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.agents.propose import propose_entry
from bookkeeper.agents.schemas import ExtractedInvoice
from bookkeeper.db.models import Account
from tests.support.factories import account, seeded_chart, settings_row, supplier


def _invoice(**changes: object) -> ExtractedInvoice:
    base: dict[str, object] = {
        "supplier_name": "Ocean Fresh",
        "invoice_no": "INV-1043",
        "invoice_date": dt.date(2026, 11, 10),
        "due_date": None,
        "terms_days": 30,
        "currency": "SGD",
        "lines": [],
        "subtotal": Decimal("400.00"),
        "gst": Decimal("36.00"),
        "total": Decimal("436.00"),
        "other_text": None,
        "suspicious_content": False,
        "confidence": Decimal("0.9"),
    }
    return ExtractedInvoice.model_validate({**base, **changes})


async def _amounts(session: AsyncSession, lines: object) -> list[tuple[str, Decimal, Decimal]]:
    out = []
    for ln in lines:  # type: ignore[attr-defined]
        acct: Account = await account(session, ln.account_id)
        out.append((acct.name, ln.debit, ln.credit))
    return out


async def test_t102_gst_registered(db_session: AsyncSession) -> None:
    await seeded_chart(db_session)
    settings = await settings_row(db_session, gst_registered=True)
    sup = await supplier(db_session, "Ocean Fresh", "COGS Seafood")
    proposal = await propose_entry(
        db_session, _invoice(), supplier=sup, settings=settings, model="m"
    )
    assert await _amounts(db_session, proposal.draft.lines) == [
        ("COGS Seafood", Decimal("400.00"), Decimal("0")),
        ("Input GST", Decimal("36.00"), Decimal("0")),
        ("Accounts Payable", Decimal("0"), Decimal("436.00")),
    ]


async def test_t103_gst_not_registered(db_session: AsyncSession) -> None:
    await seeded_chart(db_session)
    settings = await settings_row(db_session, gst_registered=False)
    sup = await supplier(db_session, "Ocean Fresh", "COGS Seafood")
    proposal = await propose_entry(
        db_session, _invoice(), supplier=sup, settings=settings, model="m"
    )
    assert await _amounts(db_session, proposal.draft.lines) == [
        ("COGS Seafood", Decimal("436.00"), Decimal("0")),
        ("Accounts Payable", Decimal("0"), Decimal("436.00")),
    ]


async def test_t044_default_account_is_used(db_session: AsyncSession) -> None:
    await seeded_chart(db_session)
    settings = await settings_row(db_session, gst_registered=False)
    sup = await supplier(db_session, "PackCo", "Packaging")
    inv = _invoice(supplier_name="PackCo", subtotal="200.00", gst="0.00", total="200.00")
    proposal = await propose_entry(db_session, inv, supplier=sup, settings=settings, model="m")
    first = await _amounts(db_session, proposal.draft.lines)
    assert first[0] == ("Packaging", Decimal("200.00"), Decimal("0"))
