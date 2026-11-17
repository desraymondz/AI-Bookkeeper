from typing import Any

from fastapi import APIRouter, Depends, FastAPI
from starlette.datastructures import MutableHeaders
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from bookkeeper.auth import routes as auth_routes
from bookkeeper.auth import test_login
from bookkeeper.auth.deps import require_boss
from bookkeeper.auth.oauth import build_google_client
from bookkeeper.config import Settings

SESSION_COOKIE = "bk_session"

# See planning/build-plan.md (Verifier notes carried forward, Auth wiring)
PUBLIC_PATH_PREFIXES: tuple[str, ...] = ("/api/auth/",)
PUBLIC_PATHS: frozenset[str] = frozenset(
    {"/api/config", "/api/test/login", "/telegram/webhook", "/health", "/api/health"}
)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PATH_PREFIXES)


class NoStoreMiddleware:
    """See planning/03-tech-stack.md section 3.2 (itsdangerous row)."""

    def __init__(self, app: ASGIApp, prefix: str = "/api") -> None:
        self.app = app
        self.prefix = prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not str(scope.get("path", "")).startswith(self.prefix):
            await self.app(scope, receive, send)
            return

        async def send_with_no_store(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, send_with_no_store)


def include_protected(app: FastAPI, router: APIRouter, **kwargs: Any) -> None:
    dependencies = [Depends(require_boss), *kwargs.pop("dependencies", [])]
    app.include_router(router, dependencies=dependencies, **kwargs)


def install_auth(app: FastAPI, settings: Settings) -> None:
    """See planning/decisions.md#D-013 and planning/01-prd.md#F-001."""
    app.state.google_oauth = build_google_client(settings)
    app.add_middleware(NoStoreMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie=SESSION_COOKIE,
        max_age=settings.session_max_age_days * 24 * 60 * 60,
        same_site="lax",
        https_only=settings.app_env != "dev",
    )
    app.include_router(auth_routes.router)
    if test_login.e2e_login_enabled(settings):
        app.include_router(test_login.router)
