"""See planning/01-prd.md#f-012-extraction-and-proposed-entry."""

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ExtractedLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    qty: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    line_total: Decimal | None = None


class ExtractedInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_name: str | None = None
    invoice_number: str | None = None
    invoice_date: dt.date | None = None
    due_date: dt.date | None = None
    currency: str | None = None
    lines: list[ExtractedLine] = []
    subtotal: Decimal | None = None
    gst: Decimal | None = None
    total: Decimal | None = None
