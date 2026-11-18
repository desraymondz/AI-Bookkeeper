"""T-005 (DB layer). See planning/decisions.md#D-035."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import EntryStatus
from bookkeeper.ledger import hold_entry, post_entry
from tests.integration.ledger.conftest import Accounts, invoice_draft

pytestmark = pytest.mark.integration

RAW_STATEMENTS = [
    "UPDATE journal_entries SET description = 'x' WHERE id = :id",
    "UPDATE journal_entries SET status = 'rejected' WHERE id = :id",
    "DELETE FROM journal_entries WHERE id = :id",
    "UPDATE journal_lines SET debit = 1.00 WHERE entry_id = :id",
    "DELETE FROM journal_lines WHERE entry_id = :id",
]


@pytest.mark.parametrize("statement", RAW_STATEMENTS)
async def test_raw_sql_cannot_change_posted_entry(
    db_session: AsyncSession, accounts: Accounts, statement: str
) -> None:
    entry = await post_entry(db_session, invoice_draft(accounts))
    with pytest.raises(DBAPIError, match="posted"):
        async with db_session.begin_nested():
            await db_session.execute(text(statement), {"id": entry.id})
    status = await db_session.scalar(
        text("SELECT status FROM journal_entries WHERE id = :id"), {"id": entry.id}
    )
    count = await db_session.scalar(
        text("SELECT count(*) FROM journal_lines WHERE entry_id = :id"), {"id": entry.id}
    )
    assert status == "posted"
    assert count == 3


async def test_raw_sql_allows_held_rewrite_and_posting_transition(
    db_session: AsyncSession, accounts: Accounts
) -> None:
    held = await hold_entry(db_session, invoice_draft(accounts))
    await db_session.execute(
        text("UPDATE journal_lines SET memo = 'edited' WHERE entry_id = :id"), {"id": held.id}
    )
    await db_session.execute(
        text("DELETE FROM journal_lines WHERE entry_id = :id"), {"id": held.id}
    )
    await db_session.execute(
        text("UPDATE journal_entries SET status = 'posted', entry_no = 7 WHERE id = :id"),
        {"id": held.id},
    )
    status = await db_session.scalar(
        text("SELECT status FROM journal_entries WHERE id = :id"), {"id": held.id}
    )
    assert status == EntryStatus.POSTED.value
