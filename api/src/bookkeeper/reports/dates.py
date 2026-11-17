"""See planning/01-prd.md#f-024-accounting-page-journal-tab-web and planning/decisions.md#D-024."""

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.ledger.periods import business_today, next_month
from bookkeeper.settings_service import get_settings


class Preset(StrEnum):
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    LAST_3_MONTHS = "last_3_months"
    YTD = "ytd"
    LAST_12_MONTHS = "last_12_months"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class DateRange:
    start: dt.date
    end: dt.date
    preset: Preset


def month_end(year: int, month: int) -> dt.date:
    ny, nm = next_month(year, month)
    return dt.date(ny, nm, 1) - dt.timedelta(days=1)


def _months_back(day: dt.date, months: int) -> dt.date:
    index = day.year * 12 + (day.month - 1) - months
    return dt.date(index // 12, index % 12 + 1, 1)


def resolve_range(
    preset: Preset,
    today: dt.date,
    fy_start_month: int = 1,
    start: dt.date | None = None,
    end: dt.date | None = None,
) -> DateRange:
    first = today.replace(day=1)
    match preset:
        case Preset.THIS_MONTH:
            return DateRange(first, today, preset)
        case Preset.LAST_MONTH:
            prev = _months_back(first, 1)
            return DateRange(prev, month_end(prev.year, prev.month), preset)
        case Preset.LAST_3_MONTHS:
            return DateRange(_months_back(first, 2), today, preset)
        case Preset.LAST_12_MONTHS:
            return DateRange(_months_back(first, 11), today, preset)
        case Preset.YTD:
            year = today.year if today.month >= fy_start_month else today.year - 1
            return DateRange(dt.date(year, fy_start_month, 1), today, preset)
        case Preset.CUSTOM:
            if start is None or end is None:
                raise ValueError("A custom range needs both start and end dates.")
            if start > end:
                raise ValueError("Start date must not be after end date.")
            return DateRange(start, end, preset)


async def resolve_range_for_business(
    session: AsyncSession,
    preset: Preset | None = None,
    start: dt.date | None = None,
    end: dt.date | None = None,
    now: dt.datetime | None = None,
) -> DateRange:
    settings = await get_settings(session)
    fy_start = settings.fy_start_month if settings is not None else 1
    today = await business_today(session, now)
    if preset is None:
        preset = Preset.CUSTOM if start is not None or end is not None else Preset.THIS_MONTH
    return resolve_range(preset, today, fy_start, start, end)
