"""See planning/04-test-spec.md (T-105 to T-116)."""

import datetime as dt
from decimal import Decimal
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.agents.schemas import ExtractedInvoice, ExtractedLine
from bookkeeper.db.models import (
    BusinessSettings,
    Document,
    DocumentKind,
    EntrySource,
    Supplier,
    User,
    UserRole,
)
from bookkeeper.ledger import EntryDraft, LineDraft
from bookkeeper.ledger.checks import CheckContext

D = Decimal
GST = Decimal("36.00")
AP = Decimal("436.00")


def make_settings(**fields: Any) -> BusinessSettings:
    values: dict[str, Any] = {
        "name": "Kopi Corner",
        "gst_registered": True,
        "gst_rate": D("9.00"),
        "dup_window_days": 180,
    }
    return BusinessSettings(**{**values, **fields})


def make_supplier(name: str = "Ocean Fresh Pte Ltd", id: int = 1, active: bool = True) -> Supplier:
    return Supplier(id=id, name=name, default_account_id=1, active=active)


def make_sender(supplier: Supplier | None, role: UserRole = UserRole.SUPPLIER) -> User:
    return User(id=7, role=role, supplier_id=None if supplier is None else supplier.id)


def make_invoice(**fields: Any) -> ExtractedInvoice:
    lines = [
        ExtractedLine(
            description="Salmon",
            unit=None,
            qty=D(10),
            unit_price=D("28.00"),
            line_total=D("280.00"),
        ),
        ExtractedLine(
            description="Prawns", unit=None, qty=D(4), unit_price=D("30.00"), line_total=D("120.00")
        ),
    ]
    values: dict[str, Any] = {
        "supplier_name": "OCEAN FRESH PTE. LTD.",
        "invoice_no": "INV-1043",
        "invoice_date": dt.date(2026, 11, 1),
        "currency": "SGD",
        "due_date": None,
        "terms_days": None,
        "suspicious_content": False,
        "confidence": Decimal("0.95"),
        "lines": lines,
        "subtotal": D("400.00"),
        "gst": D("36.00"),
        "total": D("436.00"),
    }
    return ExtractedInvoice(**{**values, **fields})


def make_entry(
    *, debit_gst: Decimal | None = GST, ap: Decimal = AP, gst_account: int = 1200
) -> EntryDraft:
    lines = [LineDraft(account_id=5010, debit=D("400.00"))]
    if debit_gst is not None:
        lines.append(LineDraft(account_id=gst_account, debit=debit_gst))
    lines.append(LineDraft(account_id=2000, credit=ap))
    return EntryDraft(
        date=dt.date(2026, 11, 1),
        description="Ocean Fresh INV-1043",
        lines=lines,
        source=EntrySource.AUTO,
    )


def make_document(sha: str = "a" * 64, id: int = 100) -> Document:
    return Document(
        id=id, path="x", sha256=sha, mime="application/pdf", size=1, kind=DocumentKind.INVOICE
    )


def make_ctx(
    session: AsyncSession | None = None,
    *,
    invoice: ExtractedInvoice | None = None,
    settings: BusinessSettings | None = None,
    supplier: Supplier | None = None,
    sender: User | None = None,
    entry: EntryDraft | None = None,
    document: Document | None = None,
) -> CheckContext:
    supplier = supplier or make_supplier()
    return CheckContext(
        session=session or cast(AsyncSession, None),
        settings=settings or make_settings(),
        supplier=supplier,
        sender_user=sender or make_sender(supplier),
        invoice=invoice or make_invoice(),
        document=document or make_document(),
        proposed_entry=entry or make_entry(),
    )
