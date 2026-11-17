"""See planning/01-prd.md#f-012-extraction-and-proposed-entry (F-012.3, F-012.4)."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.agents.schemas import ExtractedInvoice
from bookkeeper.db.models import (
    Account,
    AuditActor,
    AuditLog,
    BusinessSettings,
    EntrySource,
    Supplier,
)
from bookkeeper.ledger import EntryDraft, LineDraft
from bookkeeper.ledger.money import ZERO

INPUT_GST_NAME = "Input GST"
AP_NAME = "Accounts Payable"


class ProposalError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProposedEntry:
    draft: EntryDraft
    confidence: Decimal
    model: str


async def _account_id(session: AsyncSession, name: str) -> int:
    found = await session.scalar(
        select(Account.id).where(Account.name == name, Account.active.is_(True))
    )
    if found is None:
        raise ProposalError(f"No active account named {name!r} in the chart")
    return found


async def propose_entry(
    session: AsyncSession,
    invoice: ExtractedInvoice,
    *,
    supplier: Supplier,
    settings: BusinessSettings,
    model: str,
    ref_type: str | None = None,
    ref_id: str | int | None = None,
) -> ProposedEntry:
    if invoice.total is None or invoice.invoice_date is None:
        raise ProposalError("total and invoice date are required to propose an entry")
    total = invoice.total
    gst = invoice.gst or ZERO
    lines: list[LineDraft]
    if settings.gst_registered and gst > 0:
        subtotal = invoice.subtotal if invoice.subtotal is not None else total - gst
        lines = [
            LineDraft(supplier.default_account_id, debit=subtotal),
            LineDraft(await _account_id(session, INPUT_GST_NAME), debit=gst),
        ]
    else:
        lines = [LineDraft(supplier.default_account_id, debit=total)]
    lines.append(LineDraft(await _account_id(session, AP_NAME), credit=total))

    draft = EntryDraft(
        date=invoice.invoice_date,
        description=f"{supplier.name} {invoice.invoice_no or ''}".strip(),
        lines=lines,
        source=EntrySource.AUTO,
    )
    proposal = ProposedEntry(draft=draft, confidence=invoice.confidence, model=model)
    session.add(
        AuditLog(
            actor=AuditActor.AGENT,
            action="invoice.proposed",
            ref_type=ref_type,
            ref_id=None if ref_id is None else str(ref_id),
            model=model,
            detail_json={
                "confidence": str(invoice.confidence),
                "invoice_no": invoice.invoice_no,
                "lines": [
                    {"account_id": ln.account_id, "debit": str(ln.debit), "credit": str(ln.credit)}
                    for ln in lines
                ],
            },
        )
    )
    await session.flush()
    return proposal
