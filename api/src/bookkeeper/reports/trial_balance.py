"""See planning/01-prd.md#f-026-accounting-page-trial-balance-and-adjusted-trial-balance-tabs."""

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import AccountType, EntryKind
from bookkeeper.reports.balances import NO_MOVEMENT, ZERO, load_accounts, movements


class TrialBalanceRow(BaseModel):
    account_id: int
    code: str
    name: str
    type: AccountType
    debit: Decimal
    credit: Decimal


class TrialBalance(BaseModel):
    as_at: dt.date
    adjusted: bool
    rows: list[TrialBalanceRow]
    total_debit: Decimal
    total_credit: Decimal
    difference: Decimal


async def trial_balance(
    session: AsyncSession, as_at: dt.date, *, adjusted: bool = True
) -> TrialBalance:
    exclude = () if adjusted else (EntryKind.ADJUSTING,)
    by_account = await movements(session, end=as_at, exclude_kinds=exclude)
    rows: list[TrialBalanceRow] = []
    for account in await load_accounts(session):
        net = by_account.get(account.id, NO_MOVEMENT).net
        if net == ZERO:
            continue
        rows.append(
            TrialBalanceRow(
                account_id=account.id,
                code=account.code,
                name=account.name,
                type=account.type,
                debit=net if net > ZERO else ZERO,
                credit=-net if net < ZERO else ZERO,
            )
        )
    total_debit = sum((r.debit for r in rows), ZERO)
    total_credit = sum((r.credit for r in rows), ZERO)
    return TrialBalance(
        as_at=as_at,
        adjusted=adjusted,
        rows=rows,
        total_debit=total_debit,
        total_credit=total_credit,
        difference=total_debit - total_credit,
    )
