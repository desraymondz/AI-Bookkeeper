"""See planning/01-prd.md#f-013-deterministic-checks (F-013.10) and planning/decisions.md#D-025."""

import re
from collections.abc import Iterator
from typing import Any

from bookkeeper.ledger.checks.base import CheckContext, CheckResult

CODE = "F-013.10"

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
    invoice: Any = ctx.invoice
    sources = [
        getattr(ctx.document, "text", None),
        getattr(invoice, "raw_text", None),
        getattr(invoice, "supplier_name", None),
        getattr(invoice, "invoice_no", None),
    ]
    sources.extend(getattr(line, "description", None) for line in getattr(invoice, "lines", []))
    for source in sources:
        if isinstance(source, str) and source:
            yield source


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
    if getattr(ctx.invoice, "suspicious_content", False):
        return CheckResult(CODE, False, "Extractor flagged suspicious content")
    return CheckResult(CODE, True, None)
