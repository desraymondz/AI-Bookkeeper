"""See planning/01-prd.md#f-023-monthly-report-pack and #f-017-bills-payments-and-reminders."""

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Bill, Invoice, Payment, Supplier
from bookkeeper.ledger.periods import business_timezone
from bookkeeper.reports.balances import ZERO

BUCKETS = ("current", "days_1_30", "days_31_60", "days_61_90", "days_over_90")


def bucket_for(days_overdue: int) -> str:
    if days_overdue <= 0:
        return BUCKETS[0]
    if days_overdue <= 30:
        return BUCKETS[1]
    if days_overdue <= 60:
        return BUCKETS[2]
    if days_overdue <= 90:
        return BUCKETS[3]
    return BUCKETS[4]


class AgingBuckets(BaseModel):
    current: Decimal = ZERO
    days_1_30: Decimal = ZERO
    days_31_60: Decimal = ZERO
    days_61_90: Decimal = ZERO
    days_over_90: Decimal = ZERO
    total: Decimal = ZERO

    def add(self, bucket: str, amount: Decimal) -> None:
        setattr(self, bucket, getattr(self, bucket) + amount)
        self.total += amount


class AgingSupplierRow(AgingBuckets):
    supplier_id: int
    supplier_name: str


class AgingBill(BaseModel):
    bill_id: int
    supplier_id: int
    supplier_name: str
    invoice_no: str | None
    due_date: dt.date
    outstanding: Decimal
    days_overdue: int
    bucket: str


class ApAging(BaseModel):
    as_at: dt.date
    suppliers: list[AgingSupplierRow]
    bills: list[AgingBill]
    totals: AgingBuckets


async def ap_aging(session: AsyncSession, as_at: dt.date) -> ApAging:
    tz = await business_timezone(session)
    paid = (
        select(Payment.bill_id, func.sum(Payment.amount).label("paid"))
        .where(Payment.paid_on <= as_at)
        .group_by(Payment.bill_id)
        .subquery()
    )
    stmt = (
        select(Bill, Supplier, Invoice.invoice_no, Invoice.invoice_date, paid.c.paid)
        .join(Supplier, Supplier.id == Bill.supplier_id)
        .outerjoin(Invoice, Invoice.id == Bill.invoice_id)
        .outerjoin(paid, paid.c.bill_id == Bill.id)
        .order_by(Supplier.name, Bill.due_date, Bill.id)
    )
    totals = AgingBuckets()
    per_supplier: dict[int, AgingSupplierRow] = {}
    bills: list[AgingBill] = []
    for bill, supplier, invoice_no, invoice_date, paid_amount in (
        await session.execute(stmt)
    ).all():
        billed_on = invoice_date or bill.created_at.astimezone(tz).date()
        outstanding = bill.amount - (paid_amount or ZERO)
        if billed_on > as_at or outstanding <= ZERO:
            continue
        days = (as_at - bill.due_date).days
        bucket = bucket_for(days)
        row = per_supplier.setdefault(
            supplier.id, AgingSupplierRow(supplier_id=supplier.id, supplier_name=supplier.name)
        )
        row.add(bucket, outstanding)
        totals.add(bucket, outstanding)
        bills.append(
            AgingBill(
                bill_id=bill.id,
                supplier_id=supplier.id,
                supplier_name=supplier.name,
                invoice_no=invoice_no,
                due_date=bill.due_date,
                outstanding=outstanding,
                days_overdue=max(days, 0),
                bucket=bucket,
            )
        )
    return ApAging(as_at=as_at, suppliers=list(per_supplier.values()), bills=bills, totals=totals)
