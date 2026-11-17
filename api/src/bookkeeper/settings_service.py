"""See planning/01-prd.md#f-002-first-run-setup-and-business-settings-web and G-6."""

import datetime as dt
import re
from decimal import Decimal
from functools import cache
from typing import Annotated, Literal
from zoneinfo import available_timezones

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    field_validator,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import BusinessSettings
from bookkeeper.ledger.coa import seed_default_chart

# See planning/decisions.md#D-007
PriceRule = Literal["any_change", "increase_only"]

DEFAULT_CURRENCY = "SGD"
DEFAULT_TIMEZONE = "Asia/Singapore"
DEFAULT_FY_START_MONTH = 1
DEFAULT_GST_REGISTERED = False
DEFAULT_GST_RATE = Decimal("9.00")
DEFAULT_PRICE_RULE: PriceRule = "any_change"
DEFAULT_DUP_WINDOW_DAYS = 180
DEFAULT_REMINDER_DAYS = 3
DEFAULT_RECAP_TIME = dt.time(21, 0)
DEFAULT_REPORT_DAY = 1
DEFAULT_REPORT_TIME = dt.time(9, 0)

_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@cache
def _timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def _parse_hhmm(value: object) -> dt.time:
    if isinstance(value, dt.time):
        return value.replace(second=0, microsecond=0, tzinfo=None)
    if not isinstance(value, str):
        raise ValueError("Use HH:MM, for example 21:00")
    match = _HHMM.fullmatch(value.strip())
    if match is None:
        raise ValueError("Use HH:MM, for example 21:00")
    return dt.time(int(match.group(1)), int(match.group(2)))


HHMM = Annotated[dt.time, PlainSerializer(lambda t: t.strftime("%H:%M"), return_type=str)]
GstRate = Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]


class SettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    currency: Annotated[
        str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z]{3}$")
    ] = DEFAULT_CURRENCY
    timezone: str = DEFAULT_TIMEZONE
    fy_start_month: Annotated[int, Field(ge=1, le=12)] = DEFAULT_FY_START_MONTH
    gst_registered: bool = DEFAULT_GST_REGISTERED
    gst_rate: GstRate = DEFAULT_GST_RATE
    price_rule: PriceRule = DEFAULT_PRICE_RULE
    dup_window_days: Annotated[int, Field(ge=0, le=3650)] = DEFAULT_DUP_WINDOW_DAYS
    reminder_days: Annotated[int, Field(ge=0, le=365)] = DEFAULT_REMINDER_DAYS
    recap_time: HHMM = DEFAULT_RECAP_TIME
    report_day: Annotated[int, Field(ge=1, le=28)] = DEFAULT_REPORT_DAY
    report_time: HHMM = DEFAULT_REPORT_TIME

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        value = value.strip()
        if value not in _timezones():
            raise ValueError("Unknown IANA timezone, for example Asia/Singapore")
        return value

    @field_validator("recap_time", "report_time", mode="before")
    @classmethod
    def _check_time(cls, value: object) -> dt.time:
        return _parse_hhmm(value)


class SettingsData(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    name: str
    currency: str
    timezone: str
    fy_start_month: int
    gst_registered: bool
    gst_rate: Decimal
    price_rule: str
    dup_window_days: int
    reminder_days: int
    recap_time: HHMM
    report_day: int
    report_time: HHMM


async def _load_row(session: AsyncSession) -> BusinessSettings | None:
    result = await session.execute(select(BusinessSettings).order_by(BusinessSettings.id).limit(1))
    return result.scalar_one_or_none()


async def get_settings(session: AsyncSession) -> SettingsData | None:
    row = await _load_row(session)
    return None if row is None else SettingsData.model_validate(row)


async def save_settings(session: AsyncSession, data: SettingsInput) -> SettingsData:
    row = await _load_row(session)
    values = data.model_dump()
    if row is None:
        row = BusinessSettings(**values)
        session.add(row)
        await seed_default_chart(session)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    await session.flush()
    await session.refresh(row)
    saved = SettingsData.model_validate(row)
    await session.commit()
    return saved
