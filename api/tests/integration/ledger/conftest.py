import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account, AccountType, EntrySource, JournalEntry, JournalLine
from bookkeeper.ledger import EntryDraft, LineDraft


@dataclass(frozen=True)
class Accounts:
    cash: int
    bank: int
    cogs_seafood: int
    input_gst: int
    ap: int
    sales: int
    output_gst: int
    depreciation: int
    accum_depreciation: int
    equity: int


@pytest.fixture
async def accounts(db_session: AsyncSession) -> Accounts:
    rows = {
        "cash": ("1000", "Cash", AccountType.ASSET),
        "bank": ("1010", "Bank", AccountType.ASSET),
        "cogs_seafood": ("5010", "COGS Seafood", AccountType.EXPENSE),
        "input_gst": ("1300", "Input GST", AccountType.ASSET),
        "ap": ("2000", "Accounts Payable", AccountType.LIABILITY),
        "sales": ("4000", "Sales", AccountType.REVENUE),
        "output_gst": ("2100", "Output GST", AccountType.LIABILITY),
        "depreciation": ("6100", "Depreciation", AccountType.EXPENSE),
        "accum_depreciation": ("1590", "Accumulated Depreciation", AccountType.CONTRA_ASSET),
        "equity": ("3000", "Owner Equity", AccountType.EQUITY),
    }
    objs = {key: Account(code=c, name=n, type=t) for key, (c, n, t) in rows.items()}
    db_session.add_all(objs.values())
    await db_session.flush()
    return Accounts(**{key: obj.id for key, obj in objs.items()})


def invoice_draft(
    acc: Accounts,
    *,
    date: dt.date = dt.date(2026, 11, 10),
    source: EntrySource = EntrySource.AUTO,
    gst: Decimal = Decimal("36.00"),
) -> EntryDraft:
    return EntryDraft(
        date=date,
        description="Ocean Fresh INV-1043",
        lines=[
            LineDraft(account_id=acc.cogs_seafood, debit=Decimal("400.00")),
            LineDraft(account_id=acc.input_gst, debit=gst),
            LineDraft(account_id=acc.ap, credit=Decimal("436.00")),
        ],
        source=source,
    )


async def counts(session: AsyncSession) -> tuple[int, int]:
    entries = await session.scalar(select(func.count()).select_from(JournalEntry))
    lines = await session.scalar(select(func.count()).select_from(JournalLine))
    return int(entries or 0), int(lines or 0)


async def seed_entry_no(session: AsyncSession, entry_no: int) -> None:
    await session.execute(
        text(
            "INSERT INTO journal_entries (entry_no, date, description, source, status, kind) "
            "VALUES (:n, DATE '2026-01-01', 'Seed', 'system', 'posted', 'normal')"
        ),
        {"n": entry_no},
    )
