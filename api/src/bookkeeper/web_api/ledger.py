"""See planning/01-prd.md#f-024-accounting-page-journal-tab-web and #f-025."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper import reports
from bookkeeper.ledger.post import parse_entry_no
from bookkeeper.reports import DateRange
from bookkeeper.web_api import get_db
from bookkeeper.web_api.reports import date_range

router = APIRouter(prefix="/api", tags=["ledger"])

Db = Annotated[AsyncSession, Depends(get_db)]
Range = Annotated[DateRange, Depends(date_range)]


def _entry_no(label: str) -> int:
    try:
        return parse_entry_no(label)
    except ValueError:
        pass
    if label.isdecimal():
        return int(label)
    raise HTTPException(status_code=404, detail="Entry not found.")


@router.get("/ledger/{account_id}")
async def get_general_ledger(db: Db, account_id: int, rng: Range) -> reports.GeneralLedger:
    try:
        return await reports.general_ledger(db, account_id, rng.start, rng.end)
    except reports.AccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Account not found.") from exc


@router.get("/journal")
async def get_journal(
    db: Db, rng: Range, account_id: Annotated[int | None, Query()] = None
) -> reports.JournalListing:
    return await reports.journal_listing(db, rng.start, rng.end, account_id=account_id)


@router.get("/journal/{entry_no}")
async def get_journal_entry(db: Db, entry_no: str) -> reports.JournalEntryDetail:
    detail = await reports.journal_entry_detail(db, _entry_no(entry_no))
    if detail is None:
        raise HTTPException(status_code=404, detail="Entry not found.")
    return detail
