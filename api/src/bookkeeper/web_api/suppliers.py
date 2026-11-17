"""See planning/01-prd.md#f-007-suppliers-and-invite-links-web."""

import datetime as dt
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account, AccountType, Supplier
from bookkeeper.web_api import get_db

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])

Db = Annotated[AsyncSession, Depends(get_db)]

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Uen = Annotated[str, StringConstraints(strip_whitespace=True, max_length=32)]
Hint = Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)]


def _blank_to_none(value: Any) -> Any:
    return None if isinstance(value, str) and not value.strip() else value


class SupplierOut(BaseModel):
    id: int
    name: str
    uen: str | None
    default_account_id: int
    default_account_name: str
    terms_days: int
    telegram_username_hint: str | None
    active: bool
    created_at: dt.datetime


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    default_account_id: int
    uen: Uen | None = None
    terms_days: int = Field(default=30, ge=0, le=3650)
    telegram_username_hint: Hint | None = None

    _blank = field_validator("uen", "telegram_username_hint", mode="before")(_blank_to_none)


class SupplierUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    default_account_id: int | None = None
    uen: Uen | None = None
    terms_days: int | None = Field(default=None, ge=0, le=3650)
    telegram_username_hint: Hint | None = None
    active: bool | None = None

    _blank = field_validator("uen", "telegram_username_hint", mode="before")(_blank_to_none)


def _out(supplier: Supplier, account: Account) -> SupplierOut:
    return SupplierOut(
        id=supplier.id,
        name=supplier.name,
        uen=supplier.uen,
        default_account_id=supplier.default_account_id,
        default_account_name=account.name,
        terms_days=supplier.terms_days,
        telegram_username_hint=supplier.telegram_username_hint,
        active=supplier.active,
        created_at=supplier.created_at,
    )


def _refuse(code: int, loc: list[str], msg: str, kind: str) -> HTTPException:
    detail: list[dict[str, Any]] = [{"loc": loc, "msg": msg, "type": kind}]
    return HTTPException(status_code=code, detail=detail)


async def _expense_account(session: AsyncSession, account_id: int) -> Account:
    account = await session.get(Account, account_id)
    if account is None or not account.active or account.type != AccountType.EXPENSE:
        raise _refuse(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ["body", "default_account_id"],
            "Choose an active expense account",
            "invalid_account",
        )
    return account


async def _get_or_404(session: AsyncSession, supplier_id: int) -> Supplier:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None:
        raise _refuse(
            status.HTTP_404_NOT_FOUND, ["path", "supplier_id"], "Supplier not found", "not_found"
        )
    return supplier


@router.get("", response_model=list[SupplierOut])
async def list_suppliers(session: Db) -> list[SupplierOut]:
    rows = await session.execute(
        select(Supplier, Account)
        .join(Account, Supplier.default_account_id == Account.id)
        .order_by(Supplier.name, Supplier.id)
    )
    return [_out(supplier, account) for supplier, account in rows.all()]


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
async def create_supplier(body: SupplierCreate, session: Db) -> SupplierOut:
    account = await _expense_account(session, body.default_account_id)
    supplier = Supplier(**body.model_dump())
    session.add(supplier)
    await session.commit()
    await session.refresh(supplier)
    return _out(supplier, account)


@router.patch("/{supplier_id}", response_model=SupplierOut)
async def update_supplier(supplier_id: int, body: SupplierUpdate, session: Db) -> SupplierOut:
    supplier = await _get_or_404(session, supplier_id)
    changes = body.model_dump(exclude_unset=True)
    for required in ("name", "default_account_id", "terms_days", "active"):
        if required in changes and changes[required] is None:
            raise _refuse(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                ["body", required],
                "Value is required",
                "missing",
            )
    if "default_account_id" in changes:
        await _expense_account(session, changes["default_account_id"])
    for key, value in changes.items():
        setattr(supplier, key, value)
    await session.commit()
    await session.refresh(supplier)
    account = await session.get_one(Account, supplier.default_account_id)
    return _out(supplier, account)
