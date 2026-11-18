"""T-223, T-224, plus the D-036 eval set against a fake LLM."""

from collections.abc import Sequence
from dataclasses import replace

from eval.runner import format_table, load_samples, run_eval
from eval.samples import INVOICES
from pydantic import BaseModel

from bookkeeper.agents import services
from bookkeeper.agents.llm import LLMPart, LLMResult
from bookkeeper.config import load_settings


class InvoiceReadingLLM:
    """Implements bookkeeper.agents.llm.LLMClient by matching the invoice number in the PDF."""

    async def generate(
        self,
        *,
        task: str,
        system: str,
        parts: Sequence[LLMPart],
        schema: type[BaseModel] | None,
    ) -> LLMResult:
        blob = b"".join(p.data or b"" for p in parts)
        for spec in INVOICES.values():
            if spec.invoice_no.encode() in blob:
                return LLMResult(parsed=spec.extracted(), model="fake-flash")
        raise AssertionError(f"no sample matches for task {task!r}")


async def test_t223_eval_table_all_pass(database_url: str) -> None:
    settings = load_settings(_env_file=None)
    async with services.override(llm=InvoiceReadingLLM()):
        report = await run_eval(settings, database_url)
    table = format_table(report)
    assert table.splitlines()[0].split() == ["sample", "expected", "actual", "result"]
    assert report.passed, table
    names = [r.sample for r in report.rows]
    assert "traps auto-posted" in names
    assert "trial balance" in names


async def test_t224_wrong_expectation_fails(database_url: str) -> None:
    settings = load_settings(_env_file=None)
    samples = load_samples()
    samples[3] = replace(samples[3], expected="auto_posted")
    async with services.override(llm=InvoiceReadingLLM()):
        report = await run_eval(settings, database_url, samples)
    assert not report.passed
    assert not report.rows[3].passed
    assert "FAIL" in format_table(report)
