"""See planning/01-prd.md#f-030-seed-data-and-eval-harness, planning/04-test-spec.md."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

TODAY = dt.date(2026, 11, 18)
OPENING_DATE = dt.date(2026, 8, 1)
SEED_MONTHS: tuple[tuple[int, int], ...] = ((2026, 8), (2026, 9), (2026, 10))

BUSINESS_NAME = "Harbour Cafe"
GST_RATE = Decimal("9.00")

OPENING_BALANCES: tuple[tuple[str, str, Decimal], ...] = (
    ("1000", "debit", Decimal("2000.00")),
    ("1010", "debit", Decimal("28000.00")),
    ("3000", "credit", Decimal("30000.00")),
)


@dataclass(frozen=True, slots=True)
class SupplierSeed:
    key: str
    name: str
    uen: str
    account_code: str
    terms_days: int
    prefix: str
    first_no: int
    days: tuple[int, ...]


SUPPLIERS: tuple[SupplierSeed, ...] = (
    SupplierSeed("ocean", "Ocean Fresh", "201912345A", "5000", 30, "INV-", 1010, (3, 17)),
    SupplierSeed("dairy", "Dairy Best", "200812345B", "5010", 14, "DB-", 2001, (7, 21)),
    SupplierSeed("packco", "PackCo", "201512345C", "5100", 45, "PC-", 3001, (12,)),
)


@dataclass(frozen=True, slots=True)
class Item:
    description: str
    normalized: str
    unit: str
    unit_price: Decimal


ITEMS: dict[str, tuple[Item, ...]] = {
    "ocean": (
        Item("Salmon fillet", "salmon", "kg", Decimal("28.00")),
        Item("Prawns", "prawns", "kg", Decimal("20.00")),
        Item("Squid", "squid", "kg", Decimal("14.50")),
    ),
    "dairy": (
        Item("Fresh milk", "milk", "l", Decimal("3.20")),
        Item("Butter", "butter", "kg", Decimal("9.80")),
        Item("Cooking cream", "cream", "l", Decimal("7.50")),
    ),
    "packco": (
        Item("Paper cup 12oz", "paper cup 12oz", "each", Decimal("0.12")),
        Item("Cup lid", "cup lid", "each", Decimal("0.05")),
        Item("Takeaway bag", "takeaway bag", "each", Decimal("0.08")),
    ),
}

# Quantities per invoice, cycled by invoice sequence number, one tuple per item.
QUANTITIES: dict[str, tuple[tuple[int, int, int], ...]] = {
    "ocean": ((10, 6, 4), (12, 5, 3), (8, 7, 5), (11, 6, 2), (9, 8, 4), (10, 5, 6)),
    "dairy": ((40, 5, 6), (36, 4, 8), (44, 6, 5), (38, 5, 7), (42, 4, 6), (40, 6, 4)),
    "packco": ((1500, 1500, 800), (1800, 1800, 1000), (1600, 1600, 900)),
}

# (supplier key, invoice number) -> payment fraction of the bill total; absent means paid in full
# on the due date if that date is before TODAY, else left open.
UNPAID: frozenset[tuple[str, str]] = frozenset(
    {("ocean", "INV-1010"), ("dairy", "DB-2004"), ("packco", "PC-3003")}
)
PARTIAL: dict[tuple[str, str], Decimal] = {("ocean", "INV-1014"): Decimal("0.50")}

# Gross (GST-inclusive) takings by weekday, Monday first.
WEEKDAY_BASE: tuple[int, ...] = (780, 820, 860, 900, 1180, 1560, 1420)
DAY_STEP = Decimal("13.40")
CASH_PERCENT: tuple[int, ...] = (25, 30, 35, 40)
