"""See planning/01-prd.md#f-025-accounting-page-general-ledger-tab."""

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account, AccountType, EntryStatus, JournalEntry, JournalLine
from bookkeeper.ledger.post import format_entry_no
from bookkeeper.reports.balances import NO_MOVEMENT, ZERO, movements, natural_balance


class AccountNotFoundError(LookupError):
    pass


class LedgerPosting(BaseModel):
    date: dt.date
    entry_id: int
    entry_no: str
    description: str
    memo: str | None
    debit: Decimal
    credit: Decimal
    balance: Decimal


class GeneralLedger(BaseModel):
    account_id: int
    code: str
    name: str
    type: AccountType
    start: dt.date
    end: dt.date
    opening_balance: Decimal
    postings: list[LedgerPosting]
    total_debit: Decimal
    total_credit: Decimal
    closing_balance: Decimal


async def general_ledger(
    session: AsyncSession, account_id: int, start: dt.date, end: dt.date
) -> GeneralLedger:
    account = await session.get(Account, account_id)
    if account is None:
        raise AccountNotFoundError(account_id)
    before = (await movements(session, end=start - dt.timedelta(days=1))).get(
        account_id, NO_MOVEMENT
    )
    opening = natural_balance(account.type, before.net)
    stmt = (
        select(JournalEntry, JournalLine)
        .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
        .where(
            JournalLine.account_id == account_id,
            JournalEntry.status == EntryStatus.POSTED,
            JournalEntry.date >= start,
            JournalEntry.date <= end,
        )
        .order_by(JournalEntry.date, JournalEntry.entry_no, JournalLine.line_no)
    )
    running = opening
    postings: list[LedgerPosting] = []
    for entry, line in (await session.execute(stmt)).all():
        running += natural_balance(account.type, line.debit - line.credit)
        postings.append(
            LedgerPosting(
                date=entry.date,
                entry_id=entry.id,
                entry_no=format_entry_no(entry.entry_no) if entry.entry_no else "",
                description=entry.description,
                memo=line.memo,
                debit=line.debit,
                credit=line.credit,
                balance=running,
            )
        )
    return GeneralLedger(
        account_id=account.id,
        code=account.code,
        name=account.name,
        type=account.type,
        start=start,
        end=end,
        opening_balance=opening,
        postings=postings,
        total_debit=sum((p.debit for p in postings), ZERO),
        total_credit=sum((p.credit for p in postings), ZERO),
        closing_balance=running,
    )
