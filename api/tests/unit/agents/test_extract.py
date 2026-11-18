"""See planning/04-test-spec.md T-098, T-100, T-101."""

import json
from typing import Any

import pytest

from bookkeeper.agents.extract import ExtractionFailedError, extract_invoice
from bookkeeper.agents.llm import LLMResult
from bookkeeper.agents.schemas import ExtractedInvoice
from tests.support.fakes import FakeLLMClient

VALID: dict[str, Any] = {
    "supplier_name": "Ocean Fresh",
    "invoice_no": "INV-1043",
    "invoice_date": "2026-11-10",
    "due_date": None,
    "terms_days": 30,
    "currency": "SGD",
    "lines": [
        {
            "description": "Salmon",
            "qty": "10",
            "unit": "kg",
            "unit_price": "40.00",
            "line_total": "400.00",
        }
    ],
    "subtotal": "400.00",
    "gst": "36.00",
    "total": "436.00",
    "other_text": None,
    "suspicious_content": False,
    "confidence": "0.95",
}


def _text(**changes: object) -> LLMResult:
    return LLMResult(text=json.dumps({**VALID, **changes}), model="m")


async def test_t098_non_numeric_total_rejected() -> None:
    llm = FakeLLMClient()
    llm.set_default("extract", _text(total="abc"))
    with pytest.raises(ExtractionFailedError, match="invalid output"):
        await extract_invoice(llm, data=b"x", mime="application/pdf")


async def test_t098_missing_required_key_rejected() -> None:
    payload = {k: v for k, v in VALID.items() if k != "total"}
    llm = FakeLLMClient()
    llm.set_default("extract", LLMResult(text=json.dumps(payload), model="m"))
    with pytest.raises(ExtractionFailedError, match="invalid output"):
        await extract_invoice(llm, data=b"x", mime="application/pdf")


async def test_valid_output_parses_decimals() -> None:
    llm = FakeLLMClient()
    llm.set_default("extract", _text())
    result = await extract_invoice(llm, data=b"x", mime="application/pdf")
    assert str(result.invoice.total) == "436.00"
    assert result.model == "m"
    assert result.missing_required == []


async def test_t100_null_invoice_no_or_total_is_reported_missing() -> None:
    llm = FakeLLMClient()
    llm.set_default("extract", _text(invoice_no=None, total=None))
    result = await extract_invoice(llm, data=b"x", mime="application/pdf")
    assert result.missing_required == ["invoice_no", "total"]


async def test_t101_three_failures_means_three_attempts() -> None:
    class Failing:
        def __init__(self) -> None:
            self.count = 0

        async def generate(self, **kwargs: Any) -> LLMResult:
            self.count += 1
            raise TimeoutError("boom")

    llm = Failing()
    with pytest.raises(ExtractionFailedError) as info:
        await extract_invoice(llm, data=b"x", mime="application/pdf")
    assert llm.count == 3
    assert info.value.attempts == 3


async def test_retry_recovers_after_bad_output() -> None:
    llm = FakeLLMClient()
    llm.queue("extract", _text(total="abc"), _text())
    result = await extract_invoice(llm, data=b"x", mime="application/pdf")
    assert result.attempts == 2
    assert isinstance(result.invoice, ExtractedInvoice)


async def test_document_bytes_go_in_parts_not_system() -> None:
    llm = FakeLLMClient()
    llm.set_default("extract", _text())
    await extract_invoice(llm, data=b"DOC-MARKER", mime="application/pdf")
    call = llm.calls_for("extract")[0]
    assert "DOC-MARKER" not in call.system
    assert call.schema is ExtractedInvoice
