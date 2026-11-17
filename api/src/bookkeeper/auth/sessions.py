import datetime as dt
import hashlib
import secrets

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import WebSession

SESSION_KEY = "sid"


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


async def create_web_session(db: AsyncSession, email: str, max_age_days: int) -> str:
    """See planning/03-tech-stack.md section 3.2 (itsdangerous row)."""
    token = new_session_token()
    now = _now()
    db.add(
        WebSession(
            id=hash_session_token(token),
            email=normalize_email(email),
            expires_at=now + dt.timedelta(days=max_age_days),
            last_seen_at=now,
        )
    )
    await db.commit()
    return token


async def get_active_web_session(db: AsyncSession, token: str) -> WebSession | None:
    stmt = select(WebSession).where(
        WebSession.id == hash_session_token(token),
        WebSession.revoked_at.is_(None),
        WebSession.expires_at > _now(),
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def revoke_web_session(db: AsyncSession, token: str) -> None:
    stmt = (
        update(WebSession)
        .where(WebSession.id == hash_session_token(token), WebSession.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    await db.execute(stmt)
    await db.commit()
