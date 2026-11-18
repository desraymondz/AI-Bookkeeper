"""Inline keyboards and callback data. See planning/01-prd.md#f-015 for the approval buttons."""

from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CALLBACK_SEPARATOR = ":"
MAX_CALLBACK_BYTES = 64


@dataclass(frozen=True, slots=True)
class Button:
    label: str
    action: str
    args: tuple[str | int, ...] = ()


def encode_callback(action: str, *args: str | int) -> str:
    data = CALLBACK_SEPARATOR.join([action, *(str(arg) for arg in args)])
    if len(data.encode()) > MAX_CALLBACK_BYTES:
        raise ValueError("callback data exceeds 64 bytes")
    return data


def decode_callback(data: str) -> tuple[str, tuple[str, ...]]:
    action, *args = data.split(CALLBACK_SEPARATOR)
    return action, tuple(args)


def inline_keyboard(rows: list[list[Button]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(b.label, callback_data=encode_callback(b.action, *b.args))
                for b in row
            ]
            for row in rows
        ]
    )
