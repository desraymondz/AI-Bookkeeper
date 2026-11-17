from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bookkeeper.auth.sessions import SESSION_KEY, get_active_web_session, normalize_email
from bookkeeper.config import Settings


@dataclass(frozen=True, slots=True)
class BossSession:
    session_id: str
    email: str


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")


async def require_boss(request: Request) -> BossSession:
    """See planning/01-prd.md#F-001 and planning/build-plan.md (Auth wiring)."""
    token = request.session.get(SESSION_KEY)
    if not isinstance(token, str) or not token:
        raise _unauthorized()

    settings: Settings = request.app.state.settings
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with sessionmaker() as db:
        row = await get_active_web_session(db, token)

    if row is None or normalize_email(row.email) != normalize_email(settings.boss_email):
        raise _unauthorized()
    return BossSession(session_id=row.id, email=row.email)
