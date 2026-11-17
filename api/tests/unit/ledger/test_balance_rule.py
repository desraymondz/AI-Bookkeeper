"""T-001 to T-004. See planning/04-test-spec.md and planning/01-prd.md#global-rules (G-1)."""

import datetime as dt
from decimal import ROUND_DOWN, Decimal
from typing import Any, NoReturn, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import EntryKind, EntrySource
from bookkeeper.ledger import (
    EntryDraft,
    InvalidAmountError,
    InvalidEntryError,
    LineDraft,
    TooFewLinesError,
    UnbalancedEntryError,
    check_lines,
    post_entry,
)

COGS_SEAFOOD = 5010
INPUT_GST = 1300
AP = 2000


class ExplodingSession:
    def __getattr__(self, name: str) -> NoReturn:
        raise AssertionError(f"session.{name} used; a refused entry must write nothing")


def no_write_session() -> AsyncSession:
    return cast(AsyncSession, ExplodingSession())


def dr(account_id: int, amount: Any) -> LineDraft:
    return LineDraft(account_id=account_id, debit=amount)


def cr(account_id: int, amount: Any) -> LineDraft:
    return LineDraft(account_id=account_id, credit=amount)


def draft(*lines: LineDraft) -> EntryDraft:
    return EntryDraft(
        date=dt.date(2026, 11, 18),
        description="Test",
        lines=list(lines),
        source=EntrySource.AUTO,
    )


T001_LINES = (
    dr(COGS_SEAFOOD, Decimal("400.00")),
    dr(INPUT_GST, Decimal("36.00")),
    cr(AP, Decimal("435.00")),
)


def test_t001_unbalanced_entry_reports_difference() -> None:
    with pytest.raises(UnbalancedEntryError) as err:
        check_lines(T001_LINES)

    assert err.value.debits == Decimal("436.00")
    assert err.value.credits == Decimal("435.00")
    assert err.value.difference == Decimal("1.00")
    assert "1.00" in str(err.value)


async def test_t001_unbalanced_entry_writes_nothing() -> None:
    with pytest.raises(UnbalancedEntryError):
        await post_entry(no_write_session(), draft(*T001_LINES))


@pytest.mark.parametrize(
    ("lines", "error"),
    [
        pytest.param((dr(1, Decimal("10.00")),), TooFewLinesError, id="one-line"),
        pytest.param((), TooFewLinesError, id="no-lines"),
        pytest.param(
            (dr(1, Decimal("0.00")), cr(2, Decimal("0.00"))), InvalidAmountError, id="zero"
        ),
        pytest.param(
            (dr(1, Decimal("10.00")), cr(2, Decimal("10.00")), dr(3, Decimal("0.00"))),
            InvalidAmountError,
            id="zero-third-line",
        ),
        pytest.param(
            (dr(1, Decimal("-10.00")), cr(2, Decimal("-10.00"))),
            InvalidAmountError,
            id="negative",
        ),
        pytest.param(
            (
                LineDraft(account_id=1, debit=Decimal("10.00"), credit=Decimal("10.00")),
                cr(2, Decimal("0.01")),
            ),
            InvalidAmountError,
            id="both-sides",
        ),
    ],
)
async def test_t002_refuses_short_zero_or_negative(
    lines: tuple[LineDraft, ...], error: type[InvalidEntryError]
) -> None:
    with pytest.raises(error):
        check_lines(lines)
    with pytest.raises(error):
        await post_entry(no_write_session(), draft(*lines))


def test_t003_cents_that_float_cannot_hold_are_balanced() -> None:
    checked = check_lines((dr(1, Decimal("0.10")), dr(2, Decimal("0.20")), cr(3, Decimal("0.30"))))

    assert [line.debit for line in checked] == [Decimal("0.10"), Decimal("0.20"), Decimal("0.00")]
    assert checked[2].credit == Decimal("0.30")


async def test_t004_more_than_two_decimal_places_refused() -> None:
    lines = (dr(1, Decimal("10.005")), cr(2, Decimal("10.005")))

    with pytest.raises(InvalidAmountError, match="2 decimal places"):
        check_lines(lines)
    with pytest.raises(InvalidAmountError):
        await post_entry(no_write_session(), draft(*lines))


@pytest.mark.parametrize("amount", [10.0, 10, "10.00", True, Decimal("NaN"), Decimal("Infinity")])
def test_g1_only_finite_decimals_accepted(amount: Any) -> None:
    with pytest.raises(InvalidAmountError):
        check_lines((dr(1, amount), cr(2, Decimal("10.00"))))


def test_g1_trailing_zero_scale_is_accepted() -> None:
    checked = check_lines((dr(1, Decimal("10.500")), cr(2, Decimal("10.5"))))

    assert checked[0].debit == Decimal("10.50")
    assert checked[1].credit == Decimal("10.50")


async def test_g2_reversal_kind_only_through_reverse() -> None:
    entry = EntryDraft(
        date=dt.date(2026, 11, 18),
        description="Fake reversal",
        lines=[dr(1, Decimal("1.00")), cr(2, Decimal("1.00"))],
        source=EntrySource.MANUAL,
        kind=EntryKind.REVERSAL,
        reverses_id=1,
    )
    with pytest.raises(InvalidEntryError):
        await post_entry(no_write_session(), entry)


cents = st.integers(min_value=1, max_value=10**11).map(lambda c: Decimal(c).scaleb(-2))


@given(
    debits=st.lists(cents, min_size=1, max_size=8),
    credit_split=st.integers(min_value=1, max_value=8),
)
def test_g1_property_balanced_entries_accepted(debits: list[Decimal], credit_split: int) -> None:
    total = sum(debits, Decimal("0.00"))
    n = min(credit_split, int(total * 100))
    share = (total / n).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    credits = [share] * (n - 1) + [total - share * (n - 1)]
    lines = [dr(i, d) for i, d in enumerate(debits)] + [
        cr(100 + i, c) for i, c in enumerate(credits)
    ]

    checked = check_lines(lines)

    assert sum(line.debit for line in checked) == sum(line.credit for line in checked) == total


@given(
    debits=st.lists(cents, min_size=1, max_size=8),
    credits=st.lists(cents, min_size=1, max_size=8),
)
def test_g1_property_unbalanced_entries_refused_with_difference(
    debits: list[Decimal], credits: list[Decimal]
) -> None:
    total_dr = sum(debits, Decimal("0.00"))
    total_cr = sum(credits, Decimal("0.00"))
    lines = [dr(i, d) for i, d in enumerate(debits)] + [
        cr(100 + i, c) for i, c in enumerate(credits)
    ]

    if total_dr == total_cr:
        assert len(check_lines(lines)) == len(lines)
        return
    with pytest.raises(UnbalancedEntryError) as err:
        check_lines(lines)
    assert err.value.difference == abs(total_dr - total_cr)
