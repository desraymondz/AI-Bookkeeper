"""T-143 (parsing), T-145, T-146."""

from decimal import Decimal

from bookkeeper.agents.boss import ProposedLine, parse_sales, sales_lines, split_mismatch

D = Decimal


def test_t143_parse_sales_text() -> None:
    figures = parse_sales("sales today 1,850, cash 420, card 1,430")
    assert figures is not None
    assert (figures.total, figures.cash, figures.card) == (D("1850"), D("420"), D("1430"))
    assert not figures.yesterday
    assert not split_mismatch(figures)


def test_parse_sales_ignores_other_text() -> None:
    assert parse_sales("paid 50 cash for ice today") is None
    assert parse_sales("sales") is None


def test_t145_gst_inclusive_split() -> None:
    lines = sales_lines(D("1850"), D("420"), D("1430"), gst_registered=True, gst_rate=D("9.00"))
    assert lines == [
        ProposedLine("Cash", debit=D("420")),
        ProposedLine("Bank", debit=D("1430")),
        ProposedLine("Sales", credit=D("1697.25")),
        ProposedLine("Output GST", credit=D("152.75")),
    ]


def test_t146_not_registered_has_no_gst_line() -> None:
    lines = sales_lines(D("1850"), None, None, gst_registered=False, gst_rate=D("9.00"))
    assert lines == [ProposedLine("Cash", debit=D("1850")), ProposedLine("Sales", credit=D("1850"))]


def test_t243_split_mismatch_detected() -> None:
    figures = parse_sales("sales today 1,850, cash 420, card 1,400")
    assert figures is not None
    assert split_mismatch(figures)
