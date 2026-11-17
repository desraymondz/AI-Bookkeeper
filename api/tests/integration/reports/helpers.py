import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account, EntryKind, EntrySource, JournalEntry
from bookkeeper.ledger import EntryDraft, LineDraft, post_entry
from bookkeeper.ledger.coa import seed_default_chart

ZERO = Decimal("0.00")


def d(value: str) -> Decimal:
    return Decimal(value)


async def seed_chart(session: AsyncSession) -> dict[str, int]:
    await seed_default_chart(session)
    rows = await session.execute(select(Account.code, Account.id))
    return {code: account_id for code, account_id in rows.all()}


async def post(
    session: AsyncSession,
    ids: dict[str, int],
    day: dt.date,
    description: str,
    lines: list[tuple[str, str, str]],
    *,
    kind: EntryKind = EntryKind.NORMAL,
    source: EntrySource = EntrySource.MANUAL,
) -> JournalEntry:
    draft = EntryDraft(
        date=day,
        description=description,
        lines=[LineDraft(ids[code], d(debit), d(credit)) for code, debit, credit in lines],
        source=source,
        kind=kind,
    )
    return await post_entry(session, draft)


async def seed_three_months(session: AsyncSession, ids: dict[str, int]) -> None:
    sep, oct_, nov = dt.date(2026, 9, 1), dt.date(2026, 10, 1), dt.date(2026, 11, 1)
    await post(
        session,
        ids,
        sep,
        "Opening balances",
        [("1000", "5000.00", "0"), ("1010", "20000.00", "0"), ("3000", "0", "25000.00")],
        kind=EntryKind.OPENING,
        source=EntrySource.SYSTEM,
    )
    for month_start, rent in ((sep, "1500.00"), (oct_, "1500.00"), (nov, "1500.00")):
        y, m = month_start.year, month_start.month
        await post(
            session,
            ids,
            dt.date(y, m, 3),
            "Ocean Fresh invoice",
            [("5000", "400.00", "0"), ("1200", "36.00", "0"), ("2000", "0", "436.00")],
            source=EntrySource.AUTO,
        )
        await post(
            session,
            ids,
            dt.date(y, m, 5),
            "Daily sales",
            [("1000", "800.00", "0"), ("1010", "1200.00", "0"), ("4000", "0", "2000.00")],
        )
        await post(
            session, ids, dt.date(y, m, 10), "Rent", [("6000", rent, "0"), ("1010", "0", rent)]
        )
        await post(
            session,
            ids,
            dt.date(y, m, 20),
            "Pay Ocean Fresh",
            [("2000", "436.00", "0"), ("1010", "0", "436.00")],
        )
    await post(
        session,
        ids,
        dt.date(2026, 9, 12),
        "Espresso machine",
        [("1500", "3600.00", "0"), ("1010", "0", "3600.00")],
    )
    for last in (dt.date(2026, 9, 30), dt.date(2026, 10, 31), dt.date(2026, 11, 30)):
        await post(
            session,
            ids,
            last,
            "Depreciation",
            [("6200", "100.00", "0"), ("1510", "0", "100.00")],
            kind=EntryKind.ADJUSTING,
            source=EntrySource.SYSTEM,
        )
