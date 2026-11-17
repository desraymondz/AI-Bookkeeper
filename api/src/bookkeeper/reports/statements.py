"""See planning/01-prd.md#f-027-accounting-page-financial-statements-tabs."""

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account, AccountType, EntryKind
from bookkeeper.reports.balances import NO_MOVEMENT, ZERO, Movement, load_accounts, movements

OTHER_INCOME_SUBTYPE = "other_income"
OTHER_EXPENSE_SUBTYPE = "other_expense"
COGS_SUBTYPE = "cogs"
CASH_SUBTYPE = "cash"
FIXED_ASSET_SUBTYPE = "fixed_asset"
CURRENT_LIABILITY_SUBTYPE = "current_liability"
TRADE_PAYABLE_SUBTYPE = "trade_payable"


class StatementLine(BaseModel):
    account_id: int | None
    code: str | None
    name: str
    amount: Decimal


def _line(account: Account, amount: Decimal) -> StatementLine:
    return StatementLine(account_id=account.id, code=account.code, name=account.name, amount=amount)


def _total(lines: list[StatementLine]) -> Decimal:
    return sum((ln.amount for ln in lines), ZERO)


class ProfitAndLoss(BaseModel):
    start: dt.date
    end: dt.date
    revenue: list[StatementLine]
    total_revenue: Decimal
    cogs: list[StatementLine]
    total_cogs: Decimal
    gross_profit: Decimal
    operating_expenses: list[StatementLine]
    total_operating_expenses: Decimal
    operating_profit: Decimal
    other_items: list[StatementLine]
    total_other_items: Decimal
    net_profit: Decimal


async def profit_and_loss(session: AsyncSession, start: dt.date, end: dt.date) -> ProfitAndLoss:
    by_account = await movements(session, start=start, end=end, exclude_kinds=(EntryKind.CLOSING,))
    revenue: list[StatementLine] = []
    cogs: list[StatementLine] = []
    opex: list[StatementLine] = []
    other: list[StatementLine] = []
    for account in await load_accounts(session):
        net = by_account.get(account.id, NO_MOVEMENT).net
        if net == ZERO:
            continue
        if account.type == AccountType.REVENUE:
            target = other if account.subtype == OTHER_INCOME_SUBTYPE else revenue
            target.append(_line(account, -net))
        elif account.type == AccountType.EXPENSE:
            if account.subtype == OTHER_EXPENSE_SUBTYPE:
                other.append(_line(account, -net))
            elif account.subtype == COGS_SUBTYPE:
                cogs.append(_line(account, net))
            else:
                opex.append(_line(account, net))
    total_revenue, total_cogs = _total(revenue), _total(cogs)
    total_opex, total_other = _total(opex), _total(other)
    gross = total_revenue - total_cogs
    operating = gross - total_opex
    return ProfitAndLoss(
        start=start,
        end=end,
        revenue=revenue,
        total_revenue=total_revenue,
        cogs=cogs,
        total_cogs=total_cogs,
        gross_profit=gross,
        operating_expenses=opex,
        total_operating_expenses=total_opex,
        operating_profit=operating,
        other_items=other,
        total_other_items=total_other,
        net_profit=operating + total_other,
    )


class BalanceSheet(BaseModel):
    as_at: dt.date
    current_assets: list[StatementLine]
    total_current_assets: Decimal
    fixed_assets: list[StatementLine]
    total_fixed_assets: Decimal
    total_assets: Decimal
    liabilities: list[StatementLine]
    total_liabilities: Decimal
    equity: list[StatementLine]
    total_equity: Decimal
    total_liabilities_and_equity: Decimal
    difference: Decimal
    balanced: bool


async def balance_sheet(session: AsyncSession, as_at: dt.date) -> BalanceSheet:
    by_account = await movements(session, end=as_at)
    current: list[StatementLine] = []
    fixed: list[StatementLine] = []
    liabilities: list[StatementLine] = []
    equity: list[StatementLine] = []
    earnings = ZERO
    for account in await load_accounts(session):
        net = by_account.get(account.id, NO_MOVEMENT).net
        if net == ZERO:
            continue
        match account.type:
            case AccountType.ASSET if account.subtype != FIXED_ASSET_SUBTYPE:
                current.append(_line(account, net))
            case AccountType.ASSET | AccountType.CONTRA_ASSET:
                fixed.append(_line(account, net))
            case AccountType.LIABILITY:
                liabilities.append(_line(account, -net))
            case AccountType.EQUITY:
                equity.append(_line(account, -net))
            case AccountType.REVENUE | AccountType.EXPENSE:
                earnings -= net
    equity.append(
        StatementLine(account_id=None, code=None, name="Current period earnings", amount=earnings)
    )
    total_current, total_fixed = _total(current), _total(fixed)
    total_assets = total_current + total_fixed
    total_liabilities, total_equity = _total(liabilities), _total(equity)
    difference = total_assets - (total_liabilities + total_equity)
    return BalanceSheet(
        as_at=as_at,
        current_assets=current,
        total_current_assets=total_current,
        fixed_assets=fixed,
        total_fixed_assets=total_fixed,
        total_assets=total_assets,
        liabilities=liabilities,
        total_liabilities=total_liabilities,
        equity=equity,
        total_equity=total_equity,
        total_liabilities_and_equity=total_liabilities + total_equity,
        difference=difference,
        balanced=difference == ZERO,
    )


class CashFlow(BaseModel):
    start: dt.date
    end: dt.date
    net_profit: Decimal
    depreciation_addback: Decimal
    payables_change: list[StatementLine]
    other_working_capital: list[StatementLine]
    net_cash_from_operating: Decimal
    investing: list[StatementLine]
    net_cash_from_investing: Decimal
    financing: list[StatementLine]
    net_cash_from_financing: Decimal
    net_change: Decimal
    opening_cash: Decimal
    closing_cash: Decimal
    difference: Decimal


def _is_payable(account: Account) -> bool:
    return account.type == AccountType.LIABILITY and account.subtype == TRADE_PAYABLE_SUBTYPE


def _cash_balance(accounts: list[Account], by_account: dict[int, Movement]) -> Decimal:
    return sum(
        (
            by_account.get(a.id, NO_MOVEMENT).net
            for a in accounts
            if a.type == AccountType.ASSET and a.subtype == CASH_SUBTYPE
        ),
        ZERO,
    )


async def cash_flow(session: AsyncSession, start: dt.date, end: dt.date) -> CashFlow:
    accounts = await load_accounts(session)
    period = await movements(session, start=start, end=end, exclude_kinds=(EntryKind.CLOSING,))
    pnl = await profit_and_loss(session, start, end)
    opening = _cash_balance(accounts, await movements(session, end=start - dt.timedelta(days=1)))
    closing = _cash_balance(accounts, await movements(session, end=end))

    depreciation = ZERO
    payables: list[StatementLine] = []
    working: list[StatementLine] = []
    investing: list[StatementLine] = []
    financing: list[StatementLine] = []
    for account in accounts:
        net = period.get(account.id, NO_MOVEMENT).net
        if net == ZERO:
            continue
        cash_effect = -net
        match account.type:
            case AccountType.CONTRA_ASSET:
                depreciation += cash_effect
            case AccountType.ASSET if account.subtype == CASH_SUBTYPE:
                continue
            case AccountType.ASSET if account.subtype == FIXED_ASSET_SUBTYPE:
                investing.append(_line(account, cash_effect))
            case AccountType.ASSET:
                working.append(_line(account, cash_effect))
            case AccountType.LIABILITY if _is_payable(account):
                payables.append(_line(account, cash_effect))
            case AccountType.LIABILITY if account.subtype == CURRENT_LIABILITY_SUBTYPE:
                working.append(_line(account, cash_effect))
            case AccountType.LIABILITY | AccountType.EQUITY:
                financing.append(_line(account, cash_effect))
            case AccountType.REVENUE | AccountType.EXPENSE:
                continue
    operating = pnl.net_profit + depreciation + _total(payables) + _total(working)
    net_change = operating + _total(investing) + _total(financing)
    return CashFlow(
        start=start,
        end=end,
        net_profit=pnl.net_profit,
        depreciation_addback=depreciation,
        payables_change=payables,
        other_working_capital=working,
        net_cash_from_operating=operating,
        investing=investing,
        net_cash_from_investing=_total(investing),
        financing=financing,
        net_cash_from_financing=_total(financing),
        net_change=net_change,
        opening_cash=opening,
        closing_cash=closing,
        difference=net_change - (closing - opening),
    )
