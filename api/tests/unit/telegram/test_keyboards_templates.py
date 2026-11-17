import pytest
from jinja2 import UndefinedError

from bookkeeper.telegram.keyboards import Button, decode_callback, encode_callback, inline_keyboard
from bookkeeper.templates import render


def test_callback_round_trip() -> None:
    data = encode_callback("approve", 42, "x")
    assert decode_callback(data) == ("approve", ("42", "x"))


def test_callback_data_limit() -> None:
    with pytest.raises(ValueError, match="64 bytes"):
        encode_callback("a", "x" * 70)


def test_inline_keyboard_rows() -> None:
    markup = inline_keyboard(
        [[Button("Approve", "approve", (7,)), Button("Reject", "reject", (7,))]]
    )
    row = markup.inline_keyboard[0]
    assert [b.text for b in row] == ["Approve", "Reject"]
    assert row[0].callback_data == "approve:7"


def test_template_renders_and_is_strict() -> None:
    assert render("received", what="your invoice") == "Received your invoice."
    with pytest.raises(UndefinedError):
        render("received")
