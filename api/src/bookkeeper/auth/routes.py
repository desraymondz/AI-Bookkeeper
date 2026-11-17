from typing import Annotated, Any

from authlib.integrations.base_client.errors import OAuthError  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bookkeeper.auth.deps import BossSession, require_boss
from bookkeeper.auth.oauth import get_google_client
from bookkeeper.auth.sessions import (
    SESSION_KEY,
    create_web_session,
    normalize_email,
    revoke_web_session,
)
from bookkeeper.config import Settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _web_url(settings: Settings, path: str) -> str:
    return settings.web_app_url.rstrip("/") + path


def _is_boss(userinfo: dict[str, Any], settings: Settings) -> bool:
    email = userinfo.get("email")
    if not isinstance(email, str) or userinfo.get("email_verified") is not True:
        return False
    return normalize_email(email) == normalize_email(settings.boss_email)


async def start_boss_session(request: Request, email: str) -> None:
    settings: Settings = request.app.state.settings
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with sessionmaker() as db:
        token = await create_web_session(db, email, settings.session_max_age_days)
    request.session.clear()
    request.session[SESSION_KEY] = token


@router.get("/login")
async def login(request: Request) -> Response:
    settings: Settings = request.app.state.settings
    client = get_google_client(request)
    response: Response = await client.authorize_redirect(request, settings.google_redirect_uri)
    return response


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    """See planning/01-prd.md#F-001 (F-001.1)."""
    settings: Settings = request.app.state.settings
    client = get_google_client(request)
    try:
        token = await client.authorize_access_token(request)
    except OAuthError:
        request.session.clear()
        return RedirectResponse(_web_url(settings, "/sign-in"), status.HTTP_302_FOUND)

    userinfo = token.get("userinfo") if isinstance(token, dict) else None
    if not isinstance(userinfo, dict) or not _is_boss(userinfo, settings):
        request.session.clear()
        return RedirectResponse(_web_url(settings, "/access-denied"), status.HTTP_302_FOUND)

    await start_boss_session(request, settings.boss_email)
    return RedirectResponse(_web_url(settings, "/"), status.HTTP_302_FOUND)


@router.get("/me")
async def me(boss: Annotated[BossSession, Depends(require_boss)]) -> dict[str, str]:
    return {"email": boss.email}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request) -> Response:
    """See planning/01-prd.md#F-001 (F-001.3)."""
    token = request.session.get(SESSION_KEY)
    if isinstance(token, str) and token:
        sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
        async with sessionmaker() as db:
            await revoke_web_session(db, token)
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
