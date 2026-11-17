from fastapi import APIRouter, Request

from bookkeeper.auth.routes import start_boss_session
from bookkeeper.config import Settings

router = APIRouter(prefix="/api/test", tags=["test"])


@router.post("/login")
async def e2e_login(request: Request) -> dict[str, str]:
    """See planning/03-tech-stack.md#12-testing-strategy."""
    settings: Settings = request.app.state.settings
    await start_boss_session(request, settings.boss_email)
    return {"email": settings.boss_email}


def e2e_login_enabled(settings: Settings) -> bool:
    return settings.app_env == "test" and settings.e2e_test_login
