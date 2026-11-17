"""See planning/decisions.md#D-031."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.agents.schemas import ExtractedLine
from bookkeeper.db.models import Invoice, InvoiceLine


async def add_lines(
    session: AsyncSession,
    invoice: Invoice,
    lines: list[ExtractedLine],
    *,
    subtotal: Decimal,
    gst: Decimal,
) -> None:
    invoice.subtotal = subtotal
    invoice.gst = gst
    for number, line in enumerate(lines, start=1):
        description = line.description or ""
        session.add(
            InvoiceLine(
                invoice_id=invoice.id,
                line_no=number,
                description=description,
                normalized_item=" ".join(description.lower().split()),
                qty=line.qty,
                unit=line.unit,
                unit_price=line.unit_price,
                line_total=line.line_total,
            )
        )
    await session.flush()
