"""See planning/01-prd.md#f-030-seed-data-and-eval-harness and planning/decisions.md#D-003."""

import calendar
import datetime as dt
import hashlib
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Account,
    Asset,
    AuditActor,
    Bill,
    BillStatus,
    BusinessSettings,
    Document,
    DocumentKind,
    EntryKind,
    EntrySource,
    Invoice,
    InvoiceLine,
    JournalEntry,
    Payment,
    Supplier,
)
from bookkeeper.ledger import EntryDraft, LineDraft, post_entry
from bookkeeper.ledger.coa import seed_default_chart
from bookkeeper.settings_service import SettingsInput
from eval.seed import data

CENT = Decimal("0.01")
ASSET_NAME = "Espresso machine"
ASSET_DATE = dt.date(2026, 8, 10)
ASSET_COST = Decimal("4800.00")
ASSET_SALVAGE = Decimal("480.00")
ASSET_LIFE_MONTHS = 60


class SeedRefusedError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SeedSummary:
    suppliers: int
    invoices: int
    sales_days: int
    payments: int
    entries: int


@dataclass(frozen=True, slots=True)
class BillRef:
    bill: Bill
    supplier_key: str
    supplier_name: str
    invoice_no: str


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _stamp(day: dt.date) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(4, 0), tzinfo=dt.UTC)


async def _is_empty(session: AsyncSession) -> bool:
    for model in (BusinessSettings, Account, Supplier, JournalEntry):
        count = await session.scalar(select(func.count()).select_from(model))
        if count:
            return False
    return True


async def _post(
    session: AsyncSession,
    day: dt.date,
    description: str,
    lines: list[LineDraft],
    *,
    source: EntrySource = EntrySource.AUTO,
    kind: EntryKind = EntryKind.NORMAL,
    invoice_id: int | None = None,
) -> JournalEntry:
    draft = EntryDraft(
        date=day,
        description=description,
        lines=lines,
        source=source,
        kind=kind,
        invoice_id=invoice_id,
    )
    return await post_entry(session, draft, actor=AuditActor.SYSTEM, now=_stamp(day))


async def _account_ids(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(select(Account.code, Account.id))
    return {code: acc_id for code, acc_id in rows.all()}


async def _opening(session: AsyncSession, acc: dict[str, int]) -> None:
    lines = [
        LineDraft(
            acc[code],
            debit=amount if side == "debit" else Decimal(0),
            credit=amount if side == "credit" else Decimal(0),
        )
        for code, side, amount in data.OPENING_BALANCES
    ]
    await _post(
        session,
        data.OPENING_DATE,
        "Opening balances",
        lines,
        source=EntrySource.SYSTEM,
        kind=EntryKind.OPENING,
    )


async def _asset(session: AsyncSession, acc: dict[str, int]) -> None:
    session.add(
        Asset(
            name=ASSET_NAME,
            purchase_date=ASSET_DATE,
            cost=ASSET_COST,
            salvage=ASSET_SALVAGE,
            life_months=ASSET_LIFE_MONTHS,
            account_id=acc["1500"],
        )
    )
    await _post(
        session,
        ASSET_DATE,
        f"Purchase of {ASSET_NAME}",
        [LineDraft(acc["1500"], debit=ASSET_COST), LineDraft(acc["1010"], credit=ASSET_COST)],
        source=EntrySource.MANUAL,
    )


async def _suppliers(session: AsyncSession, acc: dict[str, int]) -> dict[str, Supplier]:
    made: dict[str, Supplier] = {}
    for seed in data.SUPPLIERS:
        supplier = Supplier(
            name=seed.name,
            uen=seed.uen,
            default_account_id=acc[seed.account_code],
            terms_days=seed.terms_days,
        )
        session.add(supplier)
        made[seed.key] = supplier
    await session.flush()
    return made


def _invoice_days(seed: data.SupplierSeed) -> list[dt.date]:
    return [dt.date(year, month, day) for year, month in data.SEED_MONTHS for day in seed.days]


async def _invoices(
    session: AsyncSession, acc: dict[str, int], suppliers: dict[str, Supplier]
) -> list[BillRef]:
    refs: list[BillRef] = []
    rate = data.GST_RATE / 100
    for seed in data.SUPPLIERS:
        supplier = suppliers[seed.key]
        quantities = data.QUANTITIES[seed.key]
        for seq, day in enumerate(_invoice_days(seed)):
            number = f"{seed.prefix}{seed.first_no + seq}"
            qtys = quantities[seq % len(quantities)]
            rows = [
                (item, Decimal(qty), money(Decimal(qty) * item.unit_price))
                for item, qty in zip(data.ITEMS[seed.key], qtys, strict=True)
            ]
            subtotal = sum((row[2] for row in rows), Decimal(0))
            gst = money(subtotal * rate)
            total = subtotal + gst
            due = day + dt.timedelta(days=seed.terms_days)

            document = Document(
                path=f"seed/{seed.key}/{number}.pdf",
                sha256=hashlib.sha256(f"seed:{seed.key}:{number}".encode()).hexdigest(),
                mime="application/pdf",
                size=0,
                kind=DocumentKind.INVOICE,
            )
            session.add(document)
            await session.flush()
            invoice = Invoice(
                document_id=document.id,
                supplier_id=supplier.id,
                invoice_no=number,
                invoice_date=day,
                due_date=due,
                currency="SGD",
                subtotal=subtotal,
                gst=gst,
                total=total,
                extraction_json={"source": "seed"},
            )
            session.add(invoice)
            await session.flush()
            session.add_all(
                InvoiceLine(
                    invoice_id=invoice.id,
                    line_no=line_no,
                    description=item.description,
                    normalized_item=item.normalized,
                    qty=qty,
                    unit=item.unit,
                    unit_price=item.unit_price,
                    line_total=line_total,
                )
                for line_no, (item, qty, line_total) in enumerate(rows, start=1)
            )
            await _post(
                session,
                day,
                f"{seed.name} {number}",
                [
                    LineDraft(acc[seed.account_code], debit=subtotal),
                    LineDraft(acc["1200"], debit=gst),
                    LineDraft(acc["2000"], credit=total),
                ],
                invoice_id=invoice.id,
            )
            bill = Bill(invoice_id=invoice.id, supplier_id=supplier.id, amount=total, due_date=due)
            session.add(bill)
            refs.append(BillRef(bill, seed.key, seed.name, number))
    await session.flush()
    return refs


async def _payments(session: AsyncSession, acc: dict[str, int], refs: list[BillRef]) -> int:
    count = 0
    for ref in refs:
        bill = ref.bill
        key = (ref.supplier_key, ref.invoice_no)
        if key in data.UNPAID or bill.due_date >= data.TODAY:
            continue
        amount = money(bill.amount * data.PARTIAL.get(key, Decimal(1)))
        entry = await _post(
            session,
            bill.due_date,
            f"Payment {ref.supplier_name} {ref.invoice_no}",
            [LineDraft(acc["2000"], debit=amount), LineDraft(acc["1010"], credit=amount)],
            source=EntrySource.BOSS_APPROVED,
        )
        session.add(
            Payment(bill_id=bill.id, entry_id=entry.id, amount=amount, paid_on=bill.due_date)
        )
        bill.paid_amount = amount
        bill.status = BillStatus.PAID if amount == bill.amount else BillStatus.OPEN
        count += 1
    await session.flush()
    return count


def daily_gross(day: dt.date) -> Decimal:
    return Decimal(data.WEEKDAY_BASE[day.weekday()]) + (day.day * 7 % 11) * data.DAY_STEP


async def _sales(session: AsyncSession, acc: dict[str, int]) -> int:
    rate = data.GST_RATE
    days = 0
    for year, month in data.SEED_MONTHS:
        for dom in range(1, calendar.monthrange(year, month)[1] + 1):
            day = dt.date(year, month, dom)
            gross = money(daily_gross(day))
            gst = money(gross * rate / (100 + rate))
            net = gross - gst
            cash_pct = data.CASH_PERCENT[day.toordinal() % len(data.CASH_PERCENT)]
            cash = money(gross * cash_pct / 100)
            card = gross - cash
            await _post(
                session,
                day,
                f"Daily sales {day.isoformat()}",
                [
                    LineDraft(acc["1000"], debit=cash),
                    LineDraft(acc["1010"], debit=card),
                    LineDraft(acc["4000"], credit=net),
                    LineDraft(acc["2100"], credit=gst),
                ],
                source=EntrySource.BOSS_APPROVED,
            )
            days += 1
    return days


async def seed_demo_cafe(session: AsyncSession, *, entries: bool = True) -> SeedSummary:
    if not await _is_empty(session):
        raise SeedRefusedError(
            "Database is not empty (settings, accounts, suppliers or entries exist). "
            "Seed only runs on an empty, migrated database."
        )
    settings = SettingsInput(name=data.BUSINESS_NAME, gst_registered=True, gst_rate=data.GST_RATE)
    session.add(BusinessSettings(**settings.model_dump()))
    await seed_default_chart(session)
    await session.flush()
    acc = await _account_ids(session)
    if not entries:
        suppliers = await _suppliers(session, acc)
        return SeedSummary(
            suppliers=len(suppliers), invoices=0, sales_days=0, payments=0, entries=0
        )
    await _opening(session, acc)
    await _asset(session, acc)
    suppliers = await _suppliers(session, acc)
    refs = await _invoices(session, acc, suppliers)
    payments = await _payments(session, acc, refs)
    sales_days = await _sales(session, acc)
    count = await session.scalar(select(func.count()).select_from(JournalEntry))
    return SeedSummary(
        suppliers=len(suppliers),
        invoices=len(refs),
        sales_days=sales_days,
        payments=payments,
        entries=int(count or 0),
    )
