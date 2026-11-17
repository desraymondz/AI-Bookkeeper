"""See planning/01-prd.md#global-rules (G-3, G-6), #F-022 and planning/decisions.md#D-024."""

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import AuditActor, AuditLog, BusinessSettings, Period, PeriodStatus

DEFAULT_TIMEZONE = "Asia/Singapore"


@dataclass(frozen=True, slots=True)
class PostingDate:
    date: dt.date
    period: Period
    original_date: dt.date
    note: str | None


def month_start(day: dt.date) -> dt.date:
    return day.replace(day=1)


def next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def format_day(day: dt.date) -> str:
    return f"{day.day} {day:%b %Y}"


def late_item_note(original: dt.date, posted_on: dt.date) -> str:
    return (
        f"Original date {format_day(original)} is in locked period {original:%b %Y}; "
        f"posted on {format_day(posted_on)}."
    )


async def business_timezone(session: AsyncSession) -> ZoneInfo:
    name = await session.scalar(
        select(BusinessSettings.timezone).order_by(BusinessSettings.id).limit(1)
    )
    return ZoneInfo(name or DEFAULT_TIMEZONE)


async def business_today(session: AsyncSession, now: dt.datetime | None = None) -> dt.date:
    instant = now or dt.datetime.now(dt.UTC)
    return instant.astimezone(await business_timezone(session)).date()


async def get_period(session: AsyncSession, year: int, month: int) -> Period | None:
    found: Period | None = await session.scalar(
        select(Period)
        .where(Period.year == year, Period.month == month)
        .execution_options(populate_existing=True)
    )
    return found


async def get_or_create_period(
    session: AsyncSession, year: int, month: int, *, lock: bool = False, share: bool = False
) -> Period:
    await session.execute(
        insert(Period)
        .values(year=year, month=month)
        .on_conflict_do_nothing(index_elements=[Period.year, Period.month])
    )
    stmt = (
        select(Period)
        .where(Period.year == year, Period.month == month)
        .execution_options(populate_existing=True)
    )
    if lock or share:
        stmt = stmt.with_for_update(read=share and not lock)
    return (await session.scalars(stmt)).one()


async def period_for_date(session: AsyncSession, day: dt.date) -> Period:
    return await get_or_create_period(session, day.year, day.month)


async def is_locked(session: AsyncSession, day: dt.date) -> bool:
    period = await get_period(session, day.year, day.month)
    return period is not None and period.status == PeriodStatus.LOCKED


async def first_open_period(
    session: AsyncSession, on_or_after: dt.date, *, share: bool = False
) -> Period:
    year, month = on_or_after.year, on_or_after.month
    while True:
        period = await get_or_create_period(session, year, month, share=share)
        if period.status != PeriodStatus.LOCKED:
            return period
        year, month = next_month(year, month)


async def resolve_posting_date(session: AsyncSession, day: dt.date) -> PostingDate:
    period = await first_open_period(session, day, share=True)
    if (period.year, period.month) == (day.year, day.month):
        return PostingDate(date=day, period=period, original_date=day, note=None)
    moved = dt.date(period.year, period.month, 1)
    return PostingDate(
        date=moved, period=period, original_date=day, note=late_item_note(day, moved)
    )


async def lock_period(
    session: AsyncSession,
    year: int,
    month: int,
    *,
    actor: AuditActor = AuditActor.SYSTEM,
    now: dt.datetime | None = None,
) -> Period:
    period = await get_or_create_period(session, year, month, lock=True)
    if period.status == PeriodStatus.LOCKED:
        return period
    period.status = PeriodStatus.LOCKED
    period.closed_at = now or dt.datetime.now(dt.UTC)
    session.add(
        AuditLog(
            actor=actor,
            action="period.locked",
            ref_type="period",
            ref_id=f"{year:04d}-{month:02d}",
            detail_json={"year": year, "month": month},
        )
    )
    await session.flush()
    return period
