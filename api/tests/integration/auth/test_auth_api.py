import re
import uuid
from typing import Any, Protocol

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import iter_route_contexts
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bookkeeper.auth.sessions import create_web_session, normalize_email
from bookkeeper.auth.wiring import SESSION_COOKIE, is_public_path
from bookkeeper.db.models import WebSession
from tests.env import DUMMY_ENV
from tests.integration.auth.conftest import (
    BOOK_MARKER,
    BOSS_EMAIL,
    DUMMY_PROTECTED_PATHS,
    AppFactory,
    ClientFactory,
    forge_session_cookie,
    set_session_cookie,
)

pytestmark = pytest.mark.integration

WEB_APP_URL = "http://localhost:5173"
PARAM = re.compile(r"\{[^}]+\}")


class Response(Protocol):
    @property
    def status_code(self) -> int: ...
    @property
    def text(self) -> str: ...
    def json(self) -> Any: ...


def _docs_paths(app: FastAPI) -> set[str]:
    paths = {app.openapi_url, app.docs_url, app.redoc_url, app.swagger_ui_oauth2_redirect_url}
    return {p for p in paths if p}


def _protected_routes(app: FastAPI) -> list[tuple[str, set[str]]]:
    docs = _docs_paths(app)
    found: list[tuple[str, set[str]]] = []
    for ctx in iter_route_contexts(app.routes):
        path = ctx.path
        if not path or path in docs or is_public_path(path):
            continue
        found.append((path, set(ctx.methods or {"GET"})))
    return found


def _protected_calls(app: FastAPI) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    for path, methods in _protected_routes(app):
        url = PARAM.sub("1", path)
        calls.extend((method, url) for method in sorted(methods))
    return calls


def _protected_paths(app: FastAPI) -> set[str]:
    return {path for path, _ in _protected_routes(app)}


def _assert_denied(response: Response) -> None:
    assert response.status_code == 401, response.text
    assert BOOK_MARKER not in response.text
    assert response.json() == {"detail": "Not signed in"}


def _assert_all_protected_denied(app: FastAPI, client: TestClient) -> None:
    calls = _protected_calls(app)
    assert calls
    for method, url in calls:
        _assert_denied(client.request(method, url))
    for path in ("/api/documents/1/file", "/api/documents/999/file"):
        _assert_denied(client.get(path))


def _mock_google(app: FastAPI, monkeypatch: pytest.MonkeyPatch, userinfo: dict[str, Any]) -> None:
    async def fake_token(request: Any, **kwargs: Any) -> dict[str, Any]:
        return {"access_token": "fake", "id_token": "fake", "userinfo": userinfo}

    monkeypatch.setattr(app.state.google_oauth, "authorize_access_token", fake_token)


async def _session_count(db_session: AsyncSession, email: str) -> int:
    stmt = select(func.count()).select_from(WebSession).where(WebSession.email == email)
    return int((await db_session.execute(stmt)).scalar_one())


def test_walker_covers_dummy_book_routes(make_app: AppFactory) -> None:
    app = make_app()

    assert _protected_paths(app) >= DUMMY_PROTECTED_PATHS


def test_t026_no_session_every_non_public_route_returns_401(
    make_app: AppFactory, make_client: ClientFactory
) -> None:
    app = make_app()
    client = make_client(app)

    _assert_all_protected_denied(app, client)
    _assert_denied(client.get("/api/auth/me"))


def test_t026_tampered_cookie_returns_401(make_app: AppFactory, make_client: ClientFactory) -> None:
    app = make_app()
    client = make_client(app)
    forged = forge_session_cookie("wrong-secret", {"sid": "anything"})
    set_session_cookie(client, forged)

    _assert_all_protected_denied(app, client)


def test_t026_unknown_session_id_returns_401(
    make_app: AppFactory, make_client: ClientFactory
) -> None:
    app = make_app()
    client = make_client(app)
    forged = forge_session_cookie(DUMMY_ENV["SESSION_SECRET"], {"sid": "not-a-real-session"})
    set_session_cookie(client, forged)

    _assert_all_protected_denied(app, client)


async def test_t025_non_boss_google_account_gets_access_denied_and_401(
    make_app: AppFactory,
    make_client: ClientFactory,
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
) -> None:
    stranger = f"stranger-{uuid.uuid4().hex[:8]}@example.com"
    app = make_app()
    client = make_client(app)
    _mock_google(app, monkeypatch, {"email": stranger, "email_verified": True})

    callback = client.get("/api/auth/callback", params={"code": "c", "state": "s"})

    assert callback.status_code == 302
    assert callback.headers["location"] == f"{WEB_APP_URL}/access-denied"
    assert await _session_count(db_session, stranger) == 0
    _assert_all_protected_denied(app, client)
    _assert_denied(client.get("/api/auth/me"))


async def test_t025_unverified_boss_email_is_denied(
    make_app: AppFactory,
    make_client: ClientFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = make_app()
    client = make_client(app)
    _mock_google(app, monkeypatch, {"email": BOSS_EMAIL, "email_verified": False})

    callback = client.get("/api/auth/callback", params={"code": "c", "state": "s"})

    assert callback.headers["location"] == f"{WEB_APP_URL}/access-denied"
    _assert_all_protected_denied(app, client)


async def test_t025_session_row_for_non_boss_email_returns_401(
    make_app: AppFactory, make_client: ClientFactory, db_engine: AsyncEngine
) -> None:
    app = make_app()
    client = make_client(app)
    async with AsyncSession(db_engine) as db:
        token = await create_web_session(db, "intruder@example.com", 14)
    set_session_cookie(client, forge_session_cookie(DUMMY_ENV["SESSION_SECRET"], {"sid": token}))

    _assert_all_protected_denied(app, client)


def test_boss_google_sign_in_opens_session(
    make_app: AppFactory, make_client: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = make_app()
    client = make_client(app)
    _mock_google(app, monkeypatch, {"email": "Boss@Example.com", "email_verified": True})

    callback = client.get("/api/auth/callback", params={"code": "c", "state": "s"})

    assert callback.status_code == 302
    assert callback.headers["location"] == f"{WEB_APP_URL}/"
    cookie = callback.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "secure" in cookie
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == {"email": normalize_email(BOSS_EMAIL)}
    assert client.get("/api/stub-journal").json()["marker"] == BOOK_MARKER


def test_login_redirects_to_google_with_state(
    make_app: AppFactory, make_client: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = make_app()
    client = make_client(app)
    metadata = {
        "issuer": "https://accounts.google.com",
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
    }

    async def fake_metadata() -> dict[str, Any]:
        app.state.google_oauth.server_metadata.update(metadata)
        return metadata

    monkeypatch.setattr(app.state.google_oauth, "load_server_metadata", fake_metadata)

    response = client.get("/api/auth/login")

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith(metadata["authorization_endpoint"])
    assert "state=" in location
    assert "scope=openid+email+profile" in location
    assert client.cookies.get(SESSION_COOKIE)


def test_t029_cookie_reused_after_sign_out_returns_401(
    make_app: AppFactory, make_client: ClientFactory
) -> None:
    app = make_app(e2e_test_login=True)
    client = make_client(app)
    assert client.post("/api/test/login").status_code == 200
    captured = client.cookies.get(SESSION_COOKIE)
    assert captured
    assert client.get("/api/auth/me").status_code == 200
    assert client.get("/api/stub-reports/trial-balance").status_code == 200

    assert client.post("/api/auth/logout").status_code == 204

    replay = make_client(app)
    set_session_cookie(replay, captured)
    _assert_all_protected_denied(app, replay)
    _assert_denied(replay.get("/api/auth/me"))


def test_t029_sign_out_ends_current_client_session(
    make_app: AppFactory, make_client: ClientFactory
) -> None:
    app = make_app(e2e_test_login=True)
    client = make_client(app)
    client.post("/api/test/login")

    client.post("/api/auth/logout")

    _assert_denied(client.get("/api/auth/me"))
    _assert_denied(client.get("/api/stub-journal"))


def test_api_responses_are_no_store(make_app: AppFactory, make_client: ClientFactory) -> None:
    app = make_app(e2e_test_login=True)
    client = make_client(app)

    assert client.get("/api/stub-journal").headers["cache-control"] == "no-store"
    assert client.post("/api/test/login").headers["cache-control"] == "no-store"
    assert client.get("/api/stub-journal").headers["cache-control"] == "no-store"
    assert client.post("/api/auth/logout").headers["cache-control"] == "no-store"


def test_test_login_returns_404_when_flag_off(
    make_app: AppFactory, make_client: ClientFactory
) -> None:
    app = make_app(e2e_test_login=False)
    client = make_client(app)

    assert client.post("/api/test/login").status_code == 404
    assert client.get("/api/test/login").status_code == 404
    assert not client.cookies.get(SESSION_COOKIE)


def test_walker_detects_route_registered_without_helper(
    make_app: AppFactory, make_client: ClientFactory
) -> None:
    app = make_app()
    leaky = APIRouter(prefix="/api/leaky")

    @leaky.get("")
    async def leaky_route() -> dict[str, str]:
        return {"marker": BOOK_MARKER}

    app.include_router(leaky)
    client = make_client(app)

    assert "/api/leaky" in _protected_paths(app)
    with pytest.raises(AssertionError):
        _assert_all_protected_denied(app, client)
