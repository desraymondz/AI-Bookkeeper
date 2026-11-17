"""See planning/01-prd.md#global-rules (G-1) and AGENTS.md hard rules."""

from decimal import Decimal, InvalidOperation

from bookkeeper.ledger.errors import InvalidAmountError

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
MAX_AMOUNT = Decimal("999999999999.99")


def to_money(value: object, *, line_no: int | None = None) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal):
        raise InvalidAmountError(
            f"amount must be a Decimal, got {type(value).__name__}", line_no=line_no
        )
    if not value.is_finite():
        raise InvalidAmountError("amount must be a finite number", line_no=line_no)
    if abs(value) > MAX_AMOUNT:
        raise InvalidAmountError(f"amount {value} is larger than {MAX_AMOUNT}", line_no=line_no)
    quantized = value.quantize(CENT)
    if quantized != value:
        raise InvalidAmountError(f"amount {value} has more than 2 decimal places", line_no=line_no)
    return quantized


def parse_money(text: str) -> Decimal:
    try:
        value = Decimal(text.strip().replace(",", ""))
    except InvalidOperation as exc:
        raise InvalidAmountError(f"{text!r} is not an amount") from exc
    return to_money(value)


def format_money(value: Decimal) -> str:
    return f"{to_money(value):,.2f}"
