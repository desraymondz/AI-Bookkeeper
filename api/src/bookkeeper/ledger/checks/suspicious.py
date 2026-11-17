"""See planning/01-prd.md#f-013-deterministic-checks (F-013.10) and planning/decisions.md#D-025."""

import re
from collections.abc import Iterator

from bookkeeper.ledger.checks.base import CheckContext, CheckResult

CODE = "suspicious"

PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+|any\s+|the\s+)?"
        r"(?:previous|prior|above|earlier|preceding)\b",
        r"\b(?:system|assistant|developer)\s*:",
        r"\bpre[-\s]?approved\b",
        r"\bauto[-\s]?approve[ds]?\b",
        r"\bapprove\s+(?:this|it|immediately)\b",
        r"\bpost\s+(?:this\s+|it\s+)?to\b",
        r"\bsend\s+(?:this\s+|it\s+)?to\s+@",
        r"\byou\s+are\s+now\b",
        r"\bdo\s+not\s+(?:flag|ask|notify|alert)\b",
        r"\bnew\s+instructions?\b",
    )
)


def _texts(ctx: CheckContext) -> Iterator[str]:
    invoice = ctx.invoice
    yield from (value for value in (invoice.supplier_name, invoice.invoice_no) if value)
    yield from (line.description for line in invoice.lines if line.description)


def find_instruction(text: str) -> str | None:
    for pattern in PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


async def run(ctx: CheckContext) -> CheckResult:
    for text in _texts(ctx):
        phrase = find_instruction(text)
        if phrase:
            return CheckResult(CODE, False, f'Instruction-like text found: "{phrase}"')
    if ctx.invoice.suspicious_content:
        return CheckResult(CODE, False, "Extractor flagged suspicious content")
    return CheckResult(CODE, True, "No instruction-like content found.")
