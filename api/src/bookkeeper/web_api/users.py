"""See planning/01-prd.md#f-008-users-and-roles-web."""

import datetime as dt
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Supplier, User, UserRole, UserStatus
from bookkeeper.web_api import get_db

router = APIRouter(prefix="/api/users", tags=["users"])

Db = Annotated[AsyncSession, Depends(get_db)]


class UserOut(BaseModel):
    id: int
    display_name: str | None
    username: str | None
    role: UserRole
    supplier_id: int | None
    supplier_name: str | None
    status: UserStatus
    linked_at: dt.datetime | None


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_id: int | None = None
    status: UserStatus | None = None
    role: UserRole | None = None


def _refuse(code: int, loc: list[str], msg: str, kind: str) -> HTTPException:
    detail: list[dict[str, Any]] = [{"loc": loc, "msg": msg, "type": kind}]
    return HTTPException(status_code=code, detail=detail)


def _out(user: User, supplier: Supplier | None) -> UserOut:
    return UserOut(
        id=user.id,
        display_name=user.display_name,
        username=user.username,
        role=user.role,
        supplier_id=user.supplier_id,
        supplier_name=supplier.name if supplier is not None else None,
        status=user.status,
        linked_at=user.linked_at,
    )


async def _get_or_404(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise _refuse(status.HTTP_404_NOT_FOUND, ["path", "user_id"], "User not found", "not_found")
    return user


async def _read(session: AsyncSession, user: User) -> UserOut:
    supplier = (
        await session.get(Supplier, user.supplier_id) if user.supplier_id is not None else None
    )
    return _out(user, supplier)


def _refuse_boss_change(loc: str) -> HTTPException:
    return _refuse(
        status.HTTP_409_CONFLICT, ["body", loc], "There is exactly one boss.", "single_boss"
    )


@router.get("", response_model=list[UserOut])
async def list_users(session: Db) -> list[UserOut]:
    rows = await session.execute(
        select(User, Supplier)
        .outerjoin(Supplier, User.supplier_id == Supplier.id)
        .where(User.telegram_user_id.is_not(None) | (User.role == UserRole.BOSS))
        .order_by(User.role, User.linked_at, User.id)
    )
    return [_out(user, supplier) for user, supplier in rows.all()]


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, body: UserUpdate, session: Db) -> UserOut:
    user = await _get_or_404(session, user_id)
    changes = body.model_dump(exclude_unset=True)

    if "role" in changes and changes["role"] != user.role:
        raise _refuse_boss_change("role")
    if user.role == UserRole.BOSS:
        if "supplier_id" in changes:
            raise _refuse_boss_change("supplier_id")
        if changes.get("status", UserStatus.ACTIVE) != UserStatus.ACTIVE:
            raise _refuse_boss_change("status")

    if "supplier_id" in changes:
        supplier = (
            await session.get(Supplier, changes["supplier_id"])
            if changes["supplier_id"] is not None
            else None
        )
        if supplier is None or not supplier.active:
            raise _refuse(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                ["body", "supplier_id"],
                "Choose an active supplier",
                "invalid_supplier",
            )
        user.supplier_id = supplier.id
    if changes.get("status") is not None:
        user.status = changes["status"]
    await session.commit()
    return await _read(session, user)


@router.post("/{user_id}/revoke", response_model=UserOut)
async def revoke_user(user_id: int, session: Db) -> UserOut:
    user = await _get_or_404(session, user_id)
    if user.role == UserRole.BOSS:
        raise _refuse_boss_change("role")
    user.status = UserStatus.DEACTIVATED
    user.telegram_user_id = None
    await session.commit()
    return await _read(session, user)
