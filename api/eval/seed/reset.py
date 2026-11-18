"""See planning/01-prd.md#f-030-seed-data-and-eval-harness."""

from dataclasses import dataclass

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import AuditLog, JournalEntry

BOOK_TABLES = (
    "journal_lines",
    "check_results",
    "approvals",
    "payments",
    "bill_reminders",
    "bills",
    "journal_entries",
    "invoice_lines",
    "invoices",
    "documents",
    "periods",
    "assets",
    "conversations",
)
BOOK_REFS = ("journal_entry", "invoice", "document", "bill", "payment", "asset")


@dataclass(frozen=True, slots=True)
class ResetSummary:
    entries: int


async def reset_books(session: AsyncSession) -> ResetSummary:
    entries = int(await session.scalar(select(func.count()).select_from(JournalEntry)) or 0)
    await session.execute(text(f"TRUNCATE {', '.join(BOOK_TABLES)} RESTART IDENTITY"))
    await session.execute(delete(AuditLog).where(AuditLog.ref_type.in_(BOOK_REFS)))
    return ResetSummary(entries=entries)
