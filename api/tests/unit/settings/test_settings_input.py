import datetime as dt
from decimal import Decimal

import pytest
from pydantic import ValidationError

from bookkeeper.settings_service import SettingsInput


def _locs(err: ValidationError) -> set[str]:
    return {str(e["loc"][0]) for e in err.errors()}


def test_defaults_match_f002_2() -> None:
    s = SettingsInput(name="Kopi Corner")

    assert s.currency == "SGD"
    assert s.timezone == "Asia/Singapore"
    assert s.fy_start_month == 1
    assert s.gst_rate == Decimal("9.00")
    assert s.price_rule == "any_change"
    assert s.dup_window_days == 180
    assert s.reminder_days == 3
    assert s.recap_time == dt.time(21, 0)
    assert s.report_day == 1
    assert s.report_time == dt.time(9, 0)


@pytest.mark.parametrize("rate", ["-1", "100.01", "101", "150"])
def test_gst_rate_out_of_range_rejected(rate: str) -> None:
    with pytest.raises(ValidationError) as err:
        SettingsInput.model_validate({"name": "X", "gst_rate": rate})
    assert _locs(err.value) == {"gst_rate"}


@pytest.mark.parametrize("rate", ["0", "100", "8", "9.5"])
def test_gst_rate_bounds_accepted(rate: str) -> None:
    assert SettingsInput.model_validate({"name": "X", "gst_rate": rate}).gst_rate == Decimal(rate)


@pytest.mark.parametrize("value", ["25:00", "9pm", "9:00", "21:60", "", "21:00:00"])
def test_bad_time_rejected(value: str) -> None:
    with pytest.raises(ValidationError) as err:
        SettingsInput.model_validate({"name": "X", "recap_time": value, "report_time": value})
    assert _locs(err.value) == {"recap_time", "report_time"}


def test_time_serialises_as_hhmm() -> None:
    s = SettingsInput.model_validate({"name": "X", "recap_time": "07:05"})
    assert s.model_dump(mode="json")["recap_time"] == "07:05"


@pytest.mark.parametrize("tz", ["Mars/Base", "Singapore Time", ""])
def test_unknown_timezone_rejected(tz: str) -> None:
    with pytest.raises(ValidationError) as err:
        SettingsInput.model_validate({"name": "X", "timezone": tz})
    assert _locs(err.value) == {"timezone"}


@pytest.mark.parametrize("month", [0, 13])
def test_fy_start_month_range(month: int) -> None:
    with pytest.raises(ValidationError) as err:
        SettingsInput.model_validate({"name": "X", "fy_start_month": month})
    assert _locs(err.value) == {"fy_start_month"}


def test_blank_name_rejected() -> None:
    with pytest.raises(ValidationError):
        SettingsInput.model_validate({"name": "   "})


def test_unknown_price_rule_rejected() -> None:
    with pytest.raises(ValidationError):
        SettingsInput.model_validate({"name": "X", "price_rule": "never"})
