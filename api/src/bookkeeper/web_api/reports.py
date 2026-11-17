"""See planning/01-prd.md#f-026-accounting-page-trial-balance-and-adjusted-trial-balance-tabs."""

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper import reports
from bookkeeper.ledger.periods import business_today
from bookkeeper.reports import DateRange, Preset
from bookkeeper.web_api import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])

Db = Annotated[AsyncSession, Depends(get_db)]


async def date_range(
    db: Db,
    preset: Annotated[Preset | None, Query()] = None,
    start: Annotated[dt.date | None, Query()] = None,
    end: Annotated[dt.date | None, Query()] = None,
) -> DateRange:
    try:
        return await reports.resolve_range_for_business(db, preset, start, end)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=[{"loc": ["query"], "msg": str(exc), "type": "value_error"}]
        ) from exc


async def as_at_date(db: Db, as_at: Annotated[dt.date | None, Query()] = None) -> dt.date:
    return as_at if as_at is not None else await business_today(db)


Range = Annotated[DateRange, Depends(date_range)]
AsAt = Annotated[dt.date, Depends(as_at_date)]


@router.get("/trial-balance")
async def get_trial_balance(db: Db, as_at: AsAt) -> reports.TrialBalance:
    return await reports.trial_balance(db, as_at, adjusted=False)


@router.get("/adjusted-trial-balance")
async def get_adjusted_trial_balance(db: Db, as_at: AsAt) -> reports.TrialBalance:
    return await reports.trial_balance(db, as_at, adjusted=True)


@router.get("/pnl")
async def get_pnl(db: Db, rng: Range) -> reports.ProfitAndLoss:
    return await reports.profit_and_loss(db, rng.start, rng.end)


@router.get("/balance-sheet")
async def get_balance_sheet(db: Db, rng: Range) -> reports.BalanceSheet:
    return await reports.balance_sheet(db, rng.end)


@router.get("/cash-flow")
async def get_cash_flow(db: Db, rng: Range) -> reports.CashFlow:
    return await reports.cash_flow(db, rng.start, rng.end)


@router.get("/ap-aging")
async def get_ap_aging(db: Db, as_at: AsAt) -> reports.ApAging:
    return await reports.ap_aging(db, as_at)
