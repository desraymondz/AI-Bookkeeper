import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bookkeeper.auth.sessions import hash_session_token, new_session_token, normalize_email
from bookkeeper.auth.test_login import e2e_login_enabled
from bookkeeper.auth.wiring import NoStoreMiddleware, is_public_path
from bookkeeper.config import load_settings


@pytest.mark.parametrize(
    "path",
    ["/api/auth/login", "/api/auth/callback", "/api/auth/me", "/api/config", "/api/test/login"],
)
def test_public_paths(path: str) -> None:
    assert is_public_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "/api/journal",
        "/api/ledger/{account_id}",
        "/api/reports/trial-balance",
        "/api/settings",
        "/api/documents/{document_id}/file",
        "/api/authx",
        "/api/test/other",
    ],
)
def test_protected_paths(path: str) -> None:
    assert not is_public_path(path)


def test_session_token_is_random_and_hashed() -> None:
    a, b = new_session_token(), new_session_token()

    assert a != b
    assert len(hash_session_token(a)) == 64
    assert hash_session_token(a) != a


def test_normalize_email() -> None:
    assert normalize_email("  Boss@Example.COM ") == "boss@example.com"


@pytest.mark.parametrize(
    ("app_env", "flag", "expected"),
    [("test", True, True), ("test", False, False), ("dev", False, False)],
)
def test_e2e_login_enabled(app_env: str, flag: bool, expected: bool) -> None:
    settings = load_settings(app_env=app_env, e2e_test_login=flag)

    assert e2e_login_enabled(settings) is expected


def test_no_store_only_on_api_paths() -> None:
    app = FastAPI()
    app.add_middleware(NoStoreMiddleware)

    @app.get("/api/thing")
    async def api_thing() -> dict[str, str]:
        return {}

    @app.get("/other")
    async def other() -> dict[str, str]:
        return {}

    client = TestClient(app)

    assert client.get("/api/thing").headers["cache-control"] == "no-store"
    assert client.get("/api/missing").headers["cache-control"] == "no-store"
    assert "cache-control" not in client.get("/other").headers
