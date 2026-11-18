"""Typed read tools for the boss assistant. See planning/01-prd.md#f-018-boss-qa."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Account,
    AccountType,
    Bill,
    BillStatus,
    EntryStatus,
    Invoice,
    JournalEntry,
    Supplier,
)
from bookkeeper.ledger.money import ZERO
from bookkeeper.reports.balances import NO_MOVEMENT, movements, natural_balance
from bookkeeper.reports.statements import profit_and_loss


@dataclass(frozen=True, slots=True)
class Amount:
    label: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class OpenBill:
    bill_id: int
    supplier: str
    invoice_no: str | None
    remaining: Decimal
    due_date: dt.date


def _like(text: str) -> str:
    return f"%{text.strip().lower()}%"


async def spend(
    session: AsyncSession, subject: str | None, start: dt.date, end: dt.date
) -> Amount | None:
    if not subject:
        pnl = await profit_and_loss(session, start, end)
        return Amount("all costs", pnl.total_cogs + pnl.total_operating_expenses)
    accounts = list(
        (
            await session.scalars(
                select(Account)
                .where(
                    Account.type == AccountType.EXPENSE,
                    func.lower(Account.name).like(_like(subject)),
                )
                .order_by(Account.code)
            )
        ).all()
    )
    if accounts:
        by_account = await movements(session, start=start, end=end)
        total = sum((by_account.get(a.id, NO_MOVEMENT).net for a in accounts), ZERO)
        return Amount(", ".join(a.name for a in accounts), total)
    supplier = await session.scalar(
        select(Supplier).where(func.lower(Supplier.name).like(_like(subject))).limit(1)
    )
    if supplier is None:
        return None
    total = await session.scalar(
        select(func.coalesce(func.sum(Invoice.subtotal), ZERO))
        .join(JournalEntry, JournalEntry.invoice_id == Invoice.id)
        .where(
            Invoice.supplier_id == supplier.id,
            JournalEntry.status == EntryStatus.POSTED,
            JournalEntry.date >= start,
            JournalEntry.date <= end,
        )
    )
    return Amount(supplier.name, total or ZERO)


async def sales(session: AsyncSession, start: dt.date, end: dt.date) -> Amount:
    pnl = await profit_and_loss(session, start, end)
    return Amount("sales", pnl.total_revenue)


async def account_balance(session: AsyncSession, subject: str, as_at: dt.date) -> Amount | None:
    account = await session.scalar(
        select(Account)
        .where(func.lower(Account.name).like(_like(subject)))
        .order_by(Account.code)
        .limit(1)
    )
    if account is None:
        return None
    by_account = await movements(session, end=as_at)
    net = by_account.get(account.id, NO_MOVEMENT).net
    return Amount(account.name, natural_balance(account.type, net))


async def open_bills(session: AsyncSession) -> list[OpenBill]:
    rows = await session.execute(
        select(Bill, Supplier.name, Invoice.invoice_no)
        .join(Supplier, Supplier.id == Bill.supplier_id)
        .outerjoin(Invoice, Invoice.id == Bill.invoice_id)
        .where(Bill.status == BillStatus.OPEN)
        .order_by(Bill.due_date, Bill.id)
    )
    return [
        OpenBill(bill.id, name, invoice_no, bill.amount - bill.paid_amount, bill.due_date)
        for bill, name, invoice_no in rows.all()
    ]
