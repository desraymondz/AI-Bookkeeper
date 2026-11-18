import pytest
from eval.seed.reset import reset_books
from eval.seed.runner import seed_demo_cafe
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Account,
    Asset,
    Bill,
    BusinessSettings,
    Invoice,
    JournalEntry,
    Supplier,
)

pytestmark = pytest.mark.integration


async def _count(session: AsyncSession, model: type) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def test_seed_without_entries(db_session: AsyncSession) -> None:
    summary = await seed_demo_cafe(db_session, entries=False)
    await db_session.commit()

    assert summary.entries == 0
    assert await _count(db_session, JournalEntry) == 0
    assert await _count(db_session, Invoice) == 0
    assert await _count(db_session, Supplier) == 3
    assert await _count(db_session, BusinessSettings) == 1
    assert await _count(db_session, Account) > 0


async def test_reset_books_keeps_setup(db_session: AsyncSession) -> None:
    await seed_demo_cafe(db_session)
    await db_session.commit()
    before = await _count(db_session, JournalEntry)

    summary = await reset_books(db_session)
    await db_session.commit()

    assert summary.entries == before > 0
    for model in (JournalEntry, Invoice, Bill, Asset):
        assert await _count(db_session, model) == 0
    assert await _count(db_session, Supplier) == 3
    assert await _count(db_session, BusinessSettings) == 1
