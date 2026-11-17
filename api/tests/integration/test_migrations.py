import datetime as dt
from decimal import Decimal
from typing import Any

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bookkeeper.db.models import (
    Account,
    AccountType,
    AuditActor,
    AuditLog,
    Base,
    EntrySource,
    JournalEntry,
    JournalLine,
)

pytestmark = pytest.mark.integration

PRD_TABLES = {
    "business_settings",
    "users",
    "strangers",
    "link_tokens",
    "suppliers",
    "accounts",
    "documents",
    "invoices",
    "invoice_lines",
    "journal_entries",
    "journal_lines",
    "check_results",
    "approvals",
    "bills",
    "payments",
    "assets",
    "periods",
    "telegram_updates",
    "scheduled_runs",
    "audit_log",
    "conversations",
    "web_sessions",
}


async def test_migration_creates_every_table(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as conn:
        tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))

    assert tables >= PRD_TABLES
    assert set(Base.metadata.tables) <= tables


async def test_migration_enables_pgvector(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as conn:
        found = await conn.scalar(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))

    assert found == "vector"


async def test_models_match_migrated_schema(db_engine: AsyncEngine) -> None:
    def diff(conn: Connection) -> list[Any]:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        return list(compare_metadata(ctx, Base.metadata))

    async with db_engine.connect() as conn:
        changes = await conn.run_sync(diff)

    assert changes == []


async def test_numeric_jsonb_and_utc_round_trip(db_session: AsyncSession) -> None:
    cash = Account(code="1000", name="Cash", type=AccountType.ASSET)
    sales = Account(code="4000", name="Sales", type=AccountType.REVENUE)
    entry = JournalEntry(
        date=dt.date(2026, 11, 18),
        description="Round trip",
        source=EntrySource.MANUAL,
    )
    db_session.add_all([cash, sales, entry])
    await db_session.flush()
    db_session.add_all(
        [
            JournalLine(entry_id=entry.id, line_no=1, account_id=cash.id, debit=Decimal("10.10")),
            JournalLine(entry_id=entry.id, line_no=2, account_id=sales.id, credit=Decimal("10.10")),
            AuditLog(
                actor=AuditActor.SYSTEM,
                action="test",
                detail_json={"amount": "10.10", "items": [1, 2]},
            ),
        ]
    )
    await db_session.flush()
    db_session.expunge_all()

    lines = (await db_session.scalars(select(JournalLine).order_by(JournalLine.line_no))).all()
    audit = (await db_session.scalars(select(AuditLog))).one()

    assert [type(line.debit) for line in lines] == [Decimal, Decimal]
    assert lines[0].debit == Decimal("10.10")
    assert lines[1].credit == Decimal("10.10")
    assert sum(line.debit for line in lines) == sum(line.credit for line in lines)
    assert audit.detail_json == {"amount": "10.10", "items": [1, 2]}
    assert audit.at.utcoffset() == dt.timedelta(0)


async def test_journal_line_rejects_both_sides_zero(db_session: AsyncSession) -> None:
    acct = Account(code="1001", name="Bank", type=AccountType.ASSET)
    entry = JournalEntry(date=dt.date(2026, 11, 18), description="Bad", source=EntrySource.MANUAL)
    db_session.add_all([acct, entry])
    await db_session.flush()
    db_session.add(JournalLine(entry_id=entry.id, line_no=1, account_id=acct.id))

    with pytest.raises(IntegrityError):
        await db_session.flush()
