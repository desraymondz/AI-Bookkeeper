"""Stand-in invoice and context builders. See planning/build-plan.md (P2-T06)."""

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, cast

from bookkeeper.db.models import BusinessSettings, Document, Supplier
from bookkeeper.ledger.checks.base import CheckContext


@dataclass
class StubLine:
    description: str
    qty: Decimal | None = Decimal("1")
    unit: str | None = "kg"
    unit_price: Decimal | None = None
    line_total: Decimal | None = None


@dataclass
class StubInvoice:
    supplier_name: str = "Ocean Fresh"
    invoice_no: str | None = "INV-1043"
    invoice_date: dt.date | None = dt.date(2026, 11, 10)
    currency: str | None = "SGD"
    subtotal: Decimal | None = Decimal("400.00")
    gst: Decimal | None = Decimal("36.00")
    total: Decimal | None = Decimal("436.00")
    lines: list[StubLine] = field(default_factory=list)
    suspicious_content: bool = False
    raw_text: str | None = None


@dataclass
class StubDocument:
    id: int = 0
    text: str | None = None


def make_ctx(
    invoice: StubInvoice,
    *,
    session: Any = None,
    settings: Any = None,
    supplier: Any = None,
    document: Any = None,
) -> CheckContext:
    return CheckContext(
        session=session,
        settings=cast(BusinessSettings, settings)
        if settings is not None
        else cast(BusinessSettings, StubSettings()),
        supplier=cast(Supplier, supplier),
        sender_user=None,
        invoice=invoice,
        document=cast(Document, document if document is not None else StubDocument()),
        proposed_entry=None,
    )


@dataclass
class StubSettings:
    currency: str = "SGD"
    timezone: str = "Asia/Singapore"
    price_rule: str = "any_change"
