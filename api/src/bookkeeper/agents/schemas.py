"""See planning/01-prd.md#f-012-extraction-and-proposed-entry."""

import datetime as dt
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Money = Annotated[Decimal, Field(allow_inf_nan=False, max_digits=16)]


class ExtractedLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None
    qty: Money | None
    unit: str | None
    unit_price: Money | None
    line_total: Money | None


class ExtractedInvoice(BaseModel):
    """Every key is required; a value the model could not read is null (F-012.2)."""

    model_config = ConfigDict(extra="forbid")

    supplier_name: str | None
    invoice_no: str | None
    invoice_date: dt.date | None
    due_date: dt.date | None
    terms_days: int | None
    currency: str | None
    lines: list[ExtractedLine]
    subtotal: Money | None
    gst: Money | None
    total: Money | None
    suspicious_content: bool
    confidence: Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]

    @property
    def missing_required(self) -> list[str]:
        return [name for name in ("invoice_no", "total") if getattr(self, name) in (None, "")]
