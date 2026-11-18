"""See planning/01-prd.md#f-013-deterministic-checks, planning/build-plan.md (P2-T05) and
planning/decisions.md#D-034."""

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.agents.schemas import ExtractedInvoice
from bookkeeper.db.models import BusinessSettings, Document, Supplier, User
from bookkeeper.ledger.post import EntryDraft


@dataclass(frozen=True, slots=True)
class CheckResult:
    code: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class CheckContext:
    session: AsyncSession
    settings: BusinessSettings
    supplier: Supplier | None
    sender_user: User | None
    invoice: ExtractedInvoice
    document: Document
    proposed_entry: EntryDraft
    current_invoice_id: int | None = None
    document_text: str | None = None


class Check(Protocol):
    CODE: str

    async def run(self, ctx: CheckContext) -> CheckResult: ...
