"""See planning/decisions.md#D-031. Journal rows are written only through bookkeeper.ledger."""

import datetime as dt
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

import pytest
from eval.seed.runner import SeedSummary, seed_demo_cafe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Account,
    BusinessSettings,
    EntryKind,
    EntrySource,
    JournalEntry,
    Supplier,
)
from bookkeeper.ledger import EntryDraft, LineDraft, post_entry
from bookkeeper.ledger.coa import seed_default_chart
from bookkeeper.settings_service import SettingsInput

AmountLine = tuple[str | int, str | Decimal, str | Decimal]


async def seeded_chart(session: AsyncSession) -> dict[str, int]:
    await seed_default_chart(session)
    rows = await session.execute(select(Account.code, Account.id))
    return {code: account_id for code, account_id in rows.all()}


async def account(session: AsyncSession, code_or_name: str | int) -> Account:
    if isinstance(code_or_name, int):
        return await session.get_one(Account, code_or_name)
    match = await session.scalar(
        select(Account).where((Account.code == code_or_name) | (Account.name == code_or_name))
    )
    if match is None:
        raise LookupError(f"No account with code or name {code_or_name!r}")
    return match


async def account_id(session: AsyncSession, ref: Account | str | int) -> int:
    if isinstance(ref, Account):
        return ref.id
    if isinstance(ref, int):
        return ref
    return (await account(session, ref)).id


async def settings_row(session: AsyncSession, **overrides: Any) -> BusinessSettings:
    values = SettingsInput(
        **{"name": "Kopi Corner", "gst_registered": True, "gst_rate": "9.00", **overrides}
    ).model_dump()
    row = BusinessSettings(**values)
    session.add(row)
    await session.flush()
    return row


async def supplier(
    session: AsyncSession,
    name: str,
    default_account: Account | str | int,
    terms_days: int = 30,
    **fields: Any,
) -> Supplier:
    row = Supplier(
        name=name,
        default_account_id=await account_id(session, default_account),
        terms_days=terms_days,
        **fields,
    )
    session.add(row)
    await session.flush()
    return row


async def post(
    session: AsyncSession,
    date: dt.date,
    lines: Sequence[AmountLine],
    *,
    source: EntrySource = EntrySource.MANUAL,
    kind: EntryKind = EntryKind.NORMAL,
    description: str = "Test entry",
) -> JournalEntry:
    drafts = [
        LineDraft(await account_id(session, ref), Decimal(debit), Decimal(credit))
        for ref, debit, credit in lines
    ]
    draft = EntryDraft(date=date, description=description, lines=drafts, source=source, kind=kind)
    return await post_entry(session, draft)


async def demo_cafe(session: AsyncSession) -> SeedSummary:
    return await seed_demo_cafe(session)


@pytest.fixture
async def ids(db_session: AsyncSession) -> dict[str, int]:
    return await seeded_chart(db_session)
