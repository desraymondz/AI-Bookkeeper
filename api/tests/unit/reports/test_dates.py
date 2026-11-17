import datetime as dt

import pytest

from bookkeeper.reports import DateRange, Preset, resolve_range
from bookkeeper.reports.ap_aging import bucket_for

TODAY = dt.date(2026, 11, 18)


def test_this_month_runs_to_today() -> None:
    assert resolve_range(Preset.THIS_MONTH, TODAY) == DateRange(
        dt.date(2026, 11, 1), TODAY, Preset.THIS_MONTH
    )


def test_last_month_is_the_whole_previous_month() -> None:
    got = resolve_range(Preset.LAST_MONTH, TODAY)
    assert (got.start, got.end) == (dt.date(2026, 10, 1), dt.date(2026, 10, 31))


def test_last_month_wraps_the_year() -> None:
    got = resolve_range(Preset.LAST_MONTH, dt.date(2027, 1, 5))
    assert (got.start, got.end) == (dt.date(2026, 12, 1), dt.date(2026, 12, 31))


def test_last_month_handles_leap_february() -> None:
    got = resolve_range(Preset.LAST_MONTH, dt.date(2028, 3, 2))
    assert got.end == dt.date(2028, 2, 29)


def test_last_3_months_includes_current() -> None:
    got = resolve_range(Preset.LAST_3_MONTHS, TODAY)
    assert (got.start, got.end) == (dt.date(2026, 9, 1), TODAY)


def test_last_12_months_includes_current() -> None:
    got = resolve_range(Preset.LAST_12_MONTHS, TODAY)
    assert (got.start, got.end) == (dt.date(2025, 12, 1), TODAY)


@pytest.mark.parametrize(
    ("fy_start", "expected"),
    [
        (1, dt.date(2026, 1, 1)),
        (4, dt.date(2026, 4, 1)),
        (11, dt.date(2026, 11, 1)),
        (12, dt.date(2025, 12, 1)),
    ],
)
def test_ytd_uses_fy_start_month(fy_start: int, expected: dt.date) -> None:
    assert resolve_range(Preset.YTD, TODAY, fy_start).start == expected


def test_custom_requires_both_dates() -> None:
    with pytest.raises(ValueError, match="both"):
        resolve_range(Preset.CUSTOM, TODAY, start=dt.date(2026, 1, 1))


def test_custom_rejects_reversed_range() -> None:
    with pytest.raises(ValueError, match="after"):
        resolve_range(Preset.CUSTOM, TODAY, start=dt.date(2026, 2, 1), end=dt.date(2026, 1, 1))


@pytest.mark.parametrize(
    ("days", "bucket"),
    [
        (-5, "current"),
        (0, "current"),
        (1, "days_1_30"),
        (30, "days_1_30"),
        (31, "days_31_60"),
        (60, "days_31_60"),
        (61, "days_61_90"),
        (90, "days_61_90"),
        (91, "days_over_90"),
    ],
)
def test_ap_buckets(days: int, bucket: str) -> None:
    assert bucket_for(days) == bucket
