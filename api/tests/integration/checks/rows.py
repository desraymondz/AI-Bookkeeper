"""Invoice rows for check tests. See planning/decisions.md#D-031."""

import datetime as dt
import itertools
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Document,
    DocumentKind,
    EntrySource,
    Invoice,
    InvoiceLine,
    Supplier,
)
from bookkeeper.ledger import EntryDraft, LineDraft, post_entry
from tests.support.factories import account_id
from tests.unit.checks.ctx_stub import StubLine

_counter = itertools.count(1)


async def add_document(session: AsyncSession) -> Document:
    n = next(_counter)
    row = Document(
        path=f"storage/test-{n}.pdf",
        sha256=f"{n:064x}",
        mime="application/pdf",
        size=1,
        kind=DocumentKind.INVOICE,
    )
    session.add(row)
    await session.flush()
    return row


async def add_invoice(
    session: AsyncSession,
    supplier: Supplier,
    invoice_no: str,
    lines: list[StubLine],
    *,
    invoice_date: dt.date = dt.date(2026, 10, 20),
    subtotal: Decimal,
    gst: Decimal,
    total: Decimal,
    posted: bool = True,
) -> Invoice:
    document = await add_document(session)
    invoice = Invoice(
        document_id=document.id,
        supplier_id=supplier.id,
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        currency="SGD",
        subtotal=subtotal,
        gst=gst,
        total=total,
    )
    session.add(invoice)
    await session.flush()
    for number, line in enumerate(lines, start=1):
        session.add(
            InvoiceLine(
                invoice_id=invoice.id,
                line_no=number,
                description=line.description,
                normalized_item=" ".join(line.description.lower().split()),
                qty=line.qty,
                unit=line.unit,
                unit_price=line.unit_price,
                line_total=line.line_total,
            )
        )
    await session.flush()
    if posted:
        await post_entry(
            session,
            EntryDraft(
                date=invoice_date,
                description=f"{supplier.name} {invoice_no}",
                lines=[
                    LineDraft(await account_id(session, "5000"), debit=subtotal),
                    LineDraft(await account_id(session, "1200"), debit=gst),
                    LineDraft(await account_id(session, "2000"), credit=total),
                ],
                source=EntrySource.AUTO,
                invoice_id=invoice.id,
            ),
        )
    return invoice
