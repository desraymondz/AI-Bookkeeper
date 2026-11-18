import datetime as dt
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import EntryKind, EntrySource
from tests.support.factories import post

ZERO = Decimal("0.00")


def d(value: str) -> Decimal:
    return Decimal(value)


async def seed_three_months(session: AsyncSession) -> None:
    sep, oct_, nov = dt.date(2026, 9, 1), dt.date(2026, 10, 1), dt.date(2026, 11, 1)
    await post(
        session,
        sep,
        [("1000", "5000.00", "0"), ("1010", "20000.00", "0"), ("3000", "0", "25000.00")],
        description="Opening balances",
        kind=EntryKind.OPENING,
        source=EntrySource.SYSTEM,
    )
    for month_start, rent in ((sep, "1500.00"), (oct_, "1500.00"), (nov, "1500.00")):
        y, m = month_start.year, month_start.month
        await post(
            session,
            dt.date(y, m, 3),
            [("5000", "400.00", "0"), ("1200", "36.00", "0"), ("2000", "0", "436.00")],
            description="Ocean Fresh invoice",
            source=EntrySource.AUTO,
        )
        await post(
            session,
            dt.date(y, m, 5),
            [("1000", "800.00", "0"), ("1010", "1200.00", "0"), ("4000", "0", "2000.00")],
            description="Daily sales",
        )
        await post(
            session,
            dt.date(y, m, 10),
            [("6000", rent, "0"), ("1010", "0", rent)],
            description="Rent",
        )
        await post(
            session,
            dt.date(y, m, 20),
            [("2000", "436.00", "0"), ("1010", "0", "436.00")],
            description="Pay Ocean Fresh",
        )
    await post(
        session,
        dt.date(2026, 9, 12),
        [("1500", "3600.00", "0"), ("1010", "0", "3600.00")],
        description="Espresso machine",
    )
    for last in (dt.date(2026, 9, 30), dt.date(2026, 10, 31), dt.date(2026, 11, 30)):
        await post(
            session,
            last,
            [("6200", "100.00", "0"), ("1510", "0", "100.00")],
            description="Depreciation",
            kind=EntryKind.ADJUSTING,
            source=EntrySource.SYSTEM,
        )
