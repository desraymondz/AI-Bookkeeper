"""See planning/01-prd.md#f-003-chart-of-accounts."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account, AccountType, Asset, JournalLine, Supplier
from bookkeeper.web_api import get_db

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

Db = Annotated[AsyncSession, Depends(get_db)]

Code = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z0-9.-]{1,16}$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Subtype = Annotated[str, StringConstraints(strip_whitespace=True, max_length=32)]


class AccountOut(BaseModel):
    id: int
    code: str
    name: str
    type: AccountType
    subtype: str | None
    active: bool
    has_postings: bool


class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Code
    name: Name
    type: AccountType
    subtype: Subtype | None = None


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    type: AccountType | None = None
    subtype: Subtype | None = None
    active: bool | None = None


def _refuse(code: int, loc: list[str], msg: str, kind: str) -> HTTPException:
    detail: list[dict[str, Any]] = [{"loc": loc, "msg": msg, "type": kind}]
    return HTTPException(status_code=code, detail=detail)


async def _has_postings(session: AsyncSession, account_id: int) -> bool:
    stmt = select(exists().where(JournalLine.account_id == account_id))
    return bool(await session.scalar(stmt))


async def _is_referenced(session: AsyncSession, account_id: int) -> bool:
    supplier = select(exists().where(Supplier.default_account_id == account_id))
    asset = select(exists().where(Asset.account_id == account_id))
    return bool(await session.scalar(supplier)) or bool(await session.scalar(asset))


async def _get_or_404(session: AsyncSession, account_id: int) -> Account:
    account = await session.get(Account, account_id)
    if account is None:
        raise _refuse(
            status.HTTP_404_NOT_FOUND, ["path", "account_id"], "Account not found", "not_found"
        )
    return account


def _out(account: Account, has_postings: bool) -> AccountOut:
    return AccountOut(
        id=account.id,
        code=account.code,
        name=account.name,
        type=account.type,
        subtype=account.subtype,
        active=account.active,
        has_postings=has_postings,
    )


@router.get("", response_model=list[AccountOut])
async def list_accounts(session: Db) -> list[AccountOut]:
    used = select(JournalLine.account_id).distinct()
    used_ids = set((await session.scalars(used)).all())
    accounts = (await session.scalars(select(Account).order_by(Account.code))).all()
    return [_out(a, a.id in used_ids) for a in accounts]


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(body: AccountCreate, session: Db) -> AccountOut:
    clash = await session.scalar(select(exists().where(Account.code == body.code)))
    if clash:
        raise _refuse(
            status.HTTP_409_CONFLICT, ["body", "code"], "Account code already exists", "duplicate"
        )
    account = Account(code=body.code, name=body.name, type=body.type, subtype=body.subtype)
    session.add(account)
    await session.flush()
    await session.refresh(account)
    out = _out(account, False)
    await session.commit()
    return out


@router.patch("/{account_id}", response_model=AccountOut)
async def update_account(account_id: int, body: AccountUpdate, session: Db) -> AccountOut:
    account = await _get_or_404(session, account_id)
    has_postings = await _has_postings(session, account_id)
    changes = body.model_dump(exclude_unset=True)

    if changes.get("type") is None:
        changes.pop("type", None)
    if changes.get("name") is None:
        changes.pop("name", None)
    if changes.get("active") is None:
        changes.pop("active", None)

    if has_postings and "type" in changes and changes["type"] != account.type:
        raise _refuse(
            status.HTTP_409_CONFLICT, ["body", "type"], "Account has postings", "has_postings"
        )
    if has_postings and changes.get("active") is False and account.active:
        raise _refuse(
            status.HTTP_409_CONFLICT, ["body", "active"], "Account has postings", "has_postings"
        )

    for key, value in changes.items():
        setattr(account, key, value)
    await session.flush()
    out = _out(account, has_postings)
    await session.commit()
    return out


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: int, session: Db) -> Response:
    account = await _get_or_404(session, account_id)
    if await _has_postings(session, account_id):
        raise _refuse(
            status.HTTP_409_CONFLICT,
            ["path", "account_id"],
            "Account has postings",
            "has_postings",
        )
    if await _is_referenced(session, account_id):
        raise _refuse(
            status.HTTP_409_CONFLICT,
            ["path", "account_id"],
            "Account is used by a supplier or asset",
            "in_use",
        )
    await session.delete(account)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
