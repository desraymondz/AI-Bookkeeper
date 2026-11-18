"""See planning/01-prd.md#f-004-opening-balances-web."""

import datetime as dt
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account
from bookkeeper.ledger import InvalidEntryError, LineDraft, format_entry_no
from bookkeeper.ledger.opening import opening_state, save_opening
from bookkeeper.web_api import get_db

router = APIRouter(prefix="/api/opening-balances", tags=["opening-balances"])

Db = Annotated[AsyncSession, Depends(get_db)]
Amount = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class OpeningLineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: int
    debit: Amount = Decimal("0.00")
    credit: Amount = Decimal("0.00")


class OpeningIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_at: dt.date
    lines: list[OpeningLineIn]


class OpeningLineOut(BaseModel):
    account_id: int
    debit: Decimal
    credit: Decimal


class OpeningOut(BaseModel):
    entry_no: str | None
    as_at: dt.date | None
    lines: list[OpeningLineOut]


class OpeningSavedOut(BaseModel):
    entry_no: str
    as_at: dt.date
    reversed_entry_no: str | None
    reversal_entry_no: str | None


def _refuse(loc: list[str], msg: str, kind: str) -> HTTPException:
    detail: list[dict[str, Any]] = [{"loc": loc, "msg": msg, "type": kind}]
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


def _label(entry_no: int | None) -> str | None:
    return format_entry_no(entry_no) if entry_no is not None else None


@router.get("", response_model=OpeningOut)
async def read_opening(session: Db) -> OpeningOut:
    state = await opening_state(session)
    return OpeningOut(
        entry_no=_label(state.entry.entry_no) if state.entry else None,
        as_at=state.entry.date if state.entry else None,
        lines=[
            OpeningLineOut(account_id=ln.account_id, debit=ln.debit, credit=ln.credit)
            for ln in state.lines
        ],
    )


@router.put("", response_model=OpeningSavedOut)
async def write_opening(body: OpeningIn, session: Db) -> OpeningSavedOut:
    ids = {ln.account_id for ln in body.lines}
    known = set((await session.scalars(select(Account.id).where(Account.id.in_(ids)))).all())
    if ids - known:
        raise _refuse(["body", "lines"], "Unknown account.", "unknown_account")
    drafts = [LineDraft(ln.account_id, debit=ln.debit, credit=ln.credit) for ln in body.lines]
    try:
        saved = await save_opening(session, body.as_at, drafts)
    except InvalidEntryError as exc:
        await session.rollback()
        raise _refuse(["body", "lines"], str(exc), "invalid_entry") from exc
    await session.commit()
    return OpeningSavedOut(
        entry_no=format_entry_no(saved.entry.entry_no or 0),
        as_at=saved.entry.date,
        reversed_entry_no=_label(saved.reversed_entry.entry_no) if saved.reversed_entry else None,
        reversal_entry_no=_label(saved.reversal.entry_no) if saved.reversal else None,
    )
