"""See planning/decisions.md#D-031."""

import datetime as dt
from decimal import Decimal
from itertools import count

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Document,
    DocumentKind,
    EntrySource,
    Invoice,
    JournalEntry,
    Supplier,
)
from bookkeeper.ledger import EntryDraft, LineDraft, post_entry

_sha = count(1)


async def add_document(session: AsyncSession) -> Document:
    doc = Document(
        path="storage/x.pdf",
        sha256=f"{next(_sha):064x}",
        mime="application/pdf",
        size=10,
        kind=DocumentKind.INVOICE,
    )
    session.add(doc)
    await session.flush()
    return doc


async def add_invoice(
    session: AsyncSession,
    supplier: Supplier,
    *,
    number: str,
    date: dt.date,
    total: Decimal,
    post_with: dict[str, int] | None = None,
    document: Document | None = None,
) -> tuple[Invoice, JournalEntry | None]:
    doc = document or await add_document(session)
    invoice = Invoice(
        document_id=doc.id,
        supplier_id=supplier.id,
        invoice_no=number,
        invoice_date=date,
        currency="SGD",
        total=total,
    )
    session.add(invoice)
    await session.flush()
    entry = None
    if post_with is not None:
        entry = await post_entry(
            session,
            EntryDraft(
                date=date,
                description=f"{supplier.name} {number}",
                lines=[
                    LineDraft(post_with["5010"], debit=total),
                    LineDraft(post_with["2000"], credit=total),
                ],
                source=EntrySource.AUTO,
                invoice_id=invoice.id,
            ),
        )
    return invoice, entry
