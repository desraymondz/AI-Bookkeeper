"""See planning/04-test-spec.md T-209."""

import datetime as dt
from decimal import Decimal

import pytest
from eval.seed.runner import SeedRefusedError, seed_demo_cafe
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Account,
    Asset,
    Bill,
    BillStatus,
    BusinessSettings,
    EntryKind,
    EntryStatus,
    Invoice,
    InvoiceLine,
    JournalEntry,
    JournalLine,
    Payment,
    Period,
    PeriodStatus,
    Supplier,
)

TODAY = dt.date(2026, 11, 18)


async def _count(session: AsyncSession, model: type) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def _balance(session: AsyncSession, code: str) -> Decimal:
    value = await session.scalar(
        select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(Account.code == code, JournalEntry.status == EntryStatus.POSTED)
    )
    return Decimal(value or 0)


async def test_t209_seed_creates_demo_cafe(db_session: AsyncSession) -> None:
    summary = await seed_demo_cafe(db_session)

    settings = (await db_session.scalars(select(BusinessSettings))).one()
    assert (settings.currency, settings.timezone) == ("SGD", "Asia/Singapore")
    assert settings.gst_registered is True
    assert settings.gst_rate == Decimal("9.00")
    assert await _count(db_session, Account) >= 15

    suppliers = {s.name: s for s in await db_session.scalars(select(Supplier))}
    assert set(suppliers) == {"Ocean Fresh", "Dairy Best", "PackCo"}
    codes = {
        a.id: a.code
        for a in await db_session.scalars(select(Account))
        if a.code in {"5000", "5010", "5100"}
    }
    assert [
        codes[suppliers[n].default_account_id] for n in ("Ocean Fresh", "Dairy Best", "PackCo")
    ] == [
        "5000",
        "5010",
        "5100",
    ]
    assert suppliers["Ocean Fresh"].terms_days == 30

    opening = (
        await db_session.scalars(select(JournalEntry).where(JournalEntry.kind == EntryKind.OPENING))
    ).all()
    assert len(opening) == 1

    assert summary.invoices == 15
    assert await _count(db_session, Invoice) == 15
    assert await _count(db_session, Bill) == 15
    assert await _count(db_session, InvoiceLine) == 45
    months = {
        (d.year, d.month)
        for d in await db_session.scalars(select(Invoice.invoice_date))
        if d is not None
    }
    assert months == {(2026, 8), (2026, 9), (2026, 10)}
    no_1043 = await db_session.scalar(select(Invoice).where(Invoice.invoice_no == "INV-1043"))
    assert no_1043 is None

    assert summary.sales_days == 92
    assert await _count(db_session, Payment) == summary.payments > 0
    assert await _count(db_session, Asset) == 1

    debits = await db_session.scalar(select(func.sum(JournalLine.debit)))
    credits = await db_session.scalar(select(func.sum(JournalLine.credit)))
    assert debits == credits
    assert await _count(db_session, JournalEntry) == summary.entries
    per_entry = await db_session.execute(
        select(JournalLine.entry_id)
        .group_by(JournalLine.entry_id)
        .having(func.sum(JournalLine.debit) != func.sum(JournalLine.credit))
    )
    assert per_entry.all() == []


async def test_seed_bills_and_ledger_agree(db_session: AsyncSession) -> None:
    await seed_demo_cafe(db_session)

    bills = (await db_session.scalars(select(Bill))).all()
    remaining = sum((b.amount - b.paid_amount for b in bills), Decimal(0))
    assert await _balance(db_session, "2000") == -remaining
    assert any(b.status == BillStatus.OPEN and b.due_date < TODAY for b in bills)
    assert any(b.status == BillStatus.OPEN and b.due_date >= TODAY for b in bills)
    assert any(b.status == BillStatus.PAID for b in bills)
    assert any(Decimal(0) < b.paid_amount < b.amount for b in bills)

    asset = (await db_session.scalars(select(Asset))).one()
    assert await _balance(db_session, "1500") == asset.cost
    assert await _balance(db_session, "1510") == 0
    assert await _balance(db_session, "6200") == 0

    locked = await db_session.scalar(
        select(func.count()).select_from(Period).where(Period.status == PeriodStatus.LOCKED)
    )
    assert locked == 0


async def test_seed_sales_split_gst_inclusive(db_session: AsyncSession) -> None:
    await seed_demo_cafe(db_session)

    sales = -await _balance(db_session, "4000")
    output_gst = -await _balance(db_session, "2100")
    assert sales > 0
    assert abs(output_gst - (sales + output_gst) * Decimal(9) / Decimal(109)) < Decimal("1.00")


async def test_seed_price_history_is_stable(db_session: AsyncSession) -> None:
    await seed_demo_cafe(db_session)

    rows = await db_session.execute(
        select(
            InvoiceLine.normalized_item, func.count(func.distinct(InvoiceLine.unit_price))
        ).group_by(InvoiceLine.normalized_item)
    )
    assert all(distinct == 1 for _, distinct in rows.all())


async def test_seed_refuses_non_empty_database(db_session: AsyncSession) -> None:
    await seed_demo_cafe(db_session)
    before = await _count(db_session, JournalEntry)

    with pytest.raises(SeedRefusedError, match="not empty"):
        await seed_demo_cafe(db_session)

    assert await _count(db_session, JournalEntry) == before
