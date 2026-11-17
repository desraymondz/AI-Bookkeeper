"""See planning/03-tech-stack.md section 3 and AGENTS.md hard rules."""

import datetime as dt
from collections.abc import Collection
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Account,
    AccountType,
    EntryKind,
    EntryStatus,
    JournalEntry,
    JournalLine,
)

ZERO = Decimal("0.00")

DEBIT_NORMAL = frozenset({AccountType.ASSET, AccountType.EXPENSE})


@dataclass(frozen=True, slots=True)
class Movement:
    debit: Decimal
    credit: Decimal

    @property
    def net(self) -> Decimal:
        return self.debit - self.credit


NO_MOVEMENT = Movement(ZERO, ZERO)


def natural_balance(account_type: AccountType, net: Decimal) -> Decimal:
    return net if account_type in DEBIT_NORMAL else -net


async def load_accounts(session: AsyncSession) -> list[Account]:
    result = await session.execute(select(Account).order_by(Account.code))
    return list(result.scalars())


async def movements(
    session: AsyncSession,
    *,
    start: dt.date | None = None,
    end: dt.date | None = None,
    exclude_kinds: Collection[EntryKind] = (),
) -> dict[int, Movement]:
    stmt = (
        select(
            JournalLine.account_id,
            func.coalesce(func.sum(JournalLine.debit), ZERO),
            func.coalesce(func.sum(JournalLine.credit), ZERO),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(JournalEntry.status == EntryStatus.POSTED)
        .group_by(JournalLine.account_id)
    )
    if start is not None:
        stmt = stmt.where(JournalEntry.date >= start)
    if end is not None:
        stmt = stmt.where(JournalEntry.date <= end)
    if exclude_kinds:
        stmt = stmt.where(JournalEntry.kind.not_in(list(exclude_kinds)))
    result = await session.execute(stmt)
    return {row[0]: Movement(row[1], row[2]) for row in result.all()}
