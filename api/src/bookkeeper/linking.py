"""Link tokens and Telegram binding. See planning/01-prd.md (F-006, F-007)."""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    AuditActor,
    AuditLog,
    LinkPurpose,
    LinkToken,
    Supplier,
    User,
    UserRole,
    UserStatus,
)

BOSS_TOKEN_TTL = dt.timedelta(hours=24)
SUPPLIER_TOKEN_TTL = dt.timedelta(days=7)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def deep_link(bot_username: str, token: str) -> str:
    return f"https://t.me/{bot_username}?start={token}"


async def create_token(
    session: AsyncSession,
    purpose: LinkPurpose,
    *,
    supplier_id: int | None = None,
    now: dt.datetime | None = None,
) -> tuple[str, LinkToken]:
    issued = now or utcnow()
    ttl = BOSS_TOKEN_TTL if purpose is LinkPurpose.BOSS else SUPPLIER_TOKEN_TTL
    token = secrets.token_urlsafe(24)
    row = LinkToken(
        token_hash=hash_token(token),
        purpose=purpose,
        supplier_id=supplier_id,
        expires_at=issued + ttl,
        created_at=issued,
    )
    session.add(row)
    await session.flush()
    return token, row


class Outcome(StrEnum):
    INVALID = "invalid"
    BOSS_LINKED = "boss_linked"
    SUPPLIER_LINKED = "supplier_linked"


@dataclass(frozen=True, slots=True)
class Redemption:
    outcome: Outcome
    supplier_name: str | None = None


INVALID = Redemption(Outcome.INVALID)


async def redeem(
    session: AsyncSession,
    token: str,
    *,
    telegram_user_id: int,
    username: str | None,
    display_name: str | None,
    now: dt.datetime | None = None,
) -> Redemption:
    moment = now or utcnow()
    row = await session.scalar(
        select(LinkToken).where(LinkToken.token_hash == hash_token(token)).with_for_update()
    )
    if row is None or row.used_at is not None or row.expires_at <= moment:
        return INVALID

    holder = await session.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
    if row.purpose is LinkPurpose.BOSS:
        result = await _bind_boss(
            session, row, holder, telegram_user_id, username, display_name, moment
        )
    else:
        result = await _bind_supplier(
            session, row, holder, telegram_user_id, username, display_name, moment
        )
    if result.outcome is Outcome.INVALID:
        return result

    row.used_at = moment
    row.used_by_telegram_user_id = telegram_user_id
    session.add(
        AuditLog(
            actor=AuditActor.SYSTEM,
            action=f"link_{row.purpose.value}",
            ref_type="link_token",
            ref_id=str(row.id),
            detail_json={"telegram_user_id": telegram_user_id},
        )
    )
    await session.flush()
    return result


async def _bind_boss(
    session: AsyncSession,
    token: LinkToken,
    holder: User | None,
    telegram_user_id: int,
    username: str | None,
    display_name: str | None,
    moment: dt.datetime,
) -> Redemption:
    boss = await session.scalar(
        select(User).where(User.role == UserRole.BOSS, User.status == UserStatus.ACTIVE)
    )
    if holder is not None and (boss is None or holder.id != boss.id):
        return INVALID
    if boss is None:
        boss = User(role=UserRole.BOSS, status=UserStatus.ACTIVE)
        session.add(boss)
    boss.telegram_user_id = telegram_user_id
    boss.username = username
    boss.display_name = display_name
    boss.linked_at = moment
    await session.flush()
    return Redemption(Outcome.BOSS_LINKED)


async def _bind_supplier(
    session: AsyncSession,
    token: LinkToken,
    holder: User | None,
    telegram_user_id: int,
    username: str | None,
    display_name: str | None,
    moment: dt.datetime,
) -> Redemption:
    supplier = (
        await session.get(Supplier, token.supplier_id) if token.supplier_id is not None else None
    )
    if supplier is None or not supplier.active:
        return INVALID
    if holder is not None and holder.role is not UserRole.SUPPLIER:
        return INVALID
    user = holder or User(telegram_user_id=telegram_user_id, role=UserRole.SUPPLIER)
    user.supplier_id = supplier.id
    user.status = UserStatus.ACTIVE
    user.username = username
    user.display_name = display_name
    user.linked_at = moment
    session.add(user)
    await session.flush()
    return Redemption(Outcome.SUPPLIER_LINKED, supplier.name)
