"""Daily recap figures. See planning/01-prd.md#f-020-daily-recap and planning/decisions.md#D-036."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Account,
    AccountType,
    EntryStatus,
    Invoice,
    JournalEntry,
    JournalLine,
)
from bookkeeper.ledger.money import ZERO
from bookkeeper.ledger.periods import business_timezone
from bookkeeper.reports.assistant import OpenBill, open_bills

OUTPUT_GST_NAME = "Output GST"


@dataclass(frozen=True, slots=True)
class RecapFigures:
    day: dt.date
    invoice_count: int
    invoice_total: Decimal
    sales_total: Decimal
    pending_count: int
    due_soon: list[OpenBill]
    overdue: list[OpenBill]


async def gross_sales(session: AsyncSession, day: dt.date) -> Decimal:
    sales_entries = (
        select(JournalLine.entry_id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(
            JournalEntry.status == EntryStatus.POSTED,
            JournalEntry.date == day,
            Account.type == AccountType.REVENUE,
            JournalLine.credit > 0,
        )
    )
    total = await session.scalar(
        select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), ZERO))
        .join(Account, Account.id == JournalLine.account_id)
        .where(
            JournalLine.entry_id.in_(sales_entries),
            (Account.type == AccountType.REVENUE) | (Account.name == OUTPUT_GST_NAME),
        )
    )
    return total or ZERO


async def daily_figures(session: AsyncSession, day: dt.date, due_within_days: int) -> RecapFigures:
    tz = await business_timezone(session)
    start = dt.datetime.combine(day, dt.time.min, tzinfo=tz)
    end = start + dt.timedelta(days=1)
    count, total = (
        await session.execute(
            select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.total), ZERO)).where(
                Invoice.created_at >= start, Invoice.created_at < end
            )
        )
    ).one()
    pending = await session.scalar(
        select(func.count(JournalEntry.id)).where(
            JournalEntry.status == EntryStatus.PENDING_APPROVAL
        )
    )
    bills = await open_bills(session)
    horizon = day + dt.timedelta(days=due_within_days)
    return RecapFigures(
        day=day,
        invoice_count=int(count),
        invoice_total=total or ZERO,
        sales_total=await gross_sales(session, day),
        pending_count=int(pending or 0),
        due_soon=[b for b in bills if day <= b.due_date <= horizon],
        overdue=[b for b in bills if b.due_date < day],
    )
