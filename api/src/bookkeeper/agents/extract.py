"""See planning/01-prd.md#f-012-extraction-and-proposed-entry and planning/decisions.md#D-016."""

from dataclasses import dataclass

from pydantic import ValidationError

from bookkeeper.agents.llm import LLMClient, LLMPart, LLMResult
from bookkeeper.agents.prompts import EXTRACT_SYSTEM
from bookkeeper.agents.schemas import ExtractedInvoice

MAX_ATTEMPTS = 3
TASK = "extract"


class ExtractionFailedError(RuntimeError):
    def __init__(self, attempts: int, last_error: str) -> None:
        super().__init__(f"extraction failed after {attempts} attempts: {last_error}")
        self.attempts = attempts
        self.last_error = last_error


class InvalidExtractionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Extraction:
    invoice: ExtractedInvoice
    model: str
    attempts: int

    @property
    def missing_required(self) -> list[str]:
        return self.invoice.missing_required


def validate_output(result: LLMResult) -> ExtractedInvoice:
    """Re-validates even an already parsed model so a bad payload never reaches propose."""
    try:
        if result.parsed is not None:
            return ExtractedInvoice.model_validate(result.parsed.model_dump())
        if result.text:
            return ExtractedInvoice.model_validate_json(result.text)
    except ValidationError as exc:
        raise InvalidExtractionError(str(exc)) from exc
    raise InvalidExtractionError("model returned no content")


async def extract_invoice(
    llm: LLMClient, *, data: bytes, mime: str, attempts: int = MAX_ATTEMPTS
) -> Extraction:
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            result = await llm.generate(
                task=TASK,
                system=EXTRACT_SYSTEM,
                parts=[
                    LLMPart.from_text("Extract this invoice."),
                    LLMPart.from_bytes(data, mime),
                ],
                schema=ExtractedInvoice,
            )
            invoice = validate_output(result)
        except InvalidExtractionError as exc:
            last_error = f"invalid output: {exc}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        else:
            return Extraction(invoice=invoice, model=result.model, attempts=attempt)
    raise ExtractionFailedError(attempts, last_error)
