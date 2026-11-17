"""See planning/01-prd.md#f-013-deterministic-checks (F-013.1)."""

import re
from difflib import SequenceMatcher

from bookkeeper.db.models import UserRole
from bookkeeper.ledger.checks.base import CheckContext, CheckResult

CODE = "known_supplier"
MATCH_RATIO = 0.85
_SUFFIXES = {"pte", "ltd", "limited", "llp", "inc", "co", "company", "sdn", "bhd", "private"}


def normalize_name(name: str) -> str:
    tokens = re.sub(r"[^a-z0-9]+", " ", name.lower()).split()
    kept = [t for t in tokens if t not in _SUFFIXES]
    return " ".join(kept or tokens)


def names_match(a: str, b: str) -> bool:
    left, right = normalize_name(a), normalize_name(b)
    if not left or not right:
        return False
    return SequenceMatcher(None, left, right).ratio() >= MATCH_RATIO


async def run(ctx: CheckContext) -> CheckResult:
    supplier, sender, extracted = ctx.supplier, ctx.sender_user, ctx.invoice.supplier_name
    if supplier is None or not supplier.active:
        return CheckResult(CODE, False, "Sender is not an active supplier.")
    if sender is None or sender.role != UserRole.SUPPLIER or sender.supplier_id != supplier.id:
        return CheckResult(CODE, False, f"Sender is not linked to {supplier.name}.")
    if not extracted or not extracted.strip():
        return CheckResult(CODE, False, f"Supplier name not read; expected {supplier.name}.")
    if not names_match(extracted, supplier.name):
        return CheckResult(
            CODE,
            False,
            f'Invoice names "{extracted}" but the sender is {supplier.name}.',
        )
    return CheckResult(CODE, True, f'Sender is {supplier.name}; invoice names "{extracted}".')
