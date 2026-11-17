"""See planning/01-prd.md#global-rules (G-1, G-3) and planning/decisions.md#D-024."""

import datetime as dt
from decimal import Decimal

import pytest

from bookkeeper.ledger import (
    InvalidAmountError,
    format_entry_no,
    late_item_note,
    parse_entry_no,
    parse_money,
    to_money,
)
from bookkeeper.ledger.periods import month_start, next_month


def test_to_money_quantizes_to_cents() -> None:
    assert str(to_money(Decimal("12.5"))) == "12.50"


@pytest.mark.parametrize("bad", [Decimal("0.001"), Decimal("1e13"), 1.5, "1.00"])
def test_to_money_refuses(bad: object) -> None:
    with pytest.raises(InvalidAmountError):
        to_money(bad)


def test_parse_money_accepts_thousand_separators() -> None:
    assert parse_money("1,850.00") == Decimal("1850.00")
    with pytest.raises(InvalidAmountError):
        parse_money("abc")


def test_entry_numbers_round_trip() -> None:
    assert format_entry_no(42) == "JE-00042"
    assert format_entry_no(123456) == "JE-123456"
    assert parse_entry_no("JE-00042") == 42
    with pytest.raises(ValueError, match="entry number"):
        parse_entry_no("JE-42")


def test_late_item_note_names_original_date() -> None:
    note = late_item_note(dt.date(2026, 10, 15), dt.date(2026, 11, 1))

    assert "15 Oct 2026" in note
    assert "1 Nov 2026" in note


def test_month_helpers() -> None:
    assert month_start(dt.date(2026, 10, 15)) == dt.date(2026, 10, 1)
    assert next_month(2026, 12) == (2027, 1)
    assert next_month(2026, 10) == (2026, 11)
