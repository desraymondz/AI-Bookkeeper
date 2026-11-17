import json
from base64 import b64encode
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

from bookkeeper.auth.wiring import SESSION_COOKIE, include_protected
from bookkeeper.config import load_settings
from bookkeeper.main import create_app
from tests.env import DUMMY_ENV

BOSS_EMAIL = DUMMY_ENV["BOSS_EMAIL"]
BOOK_MARKER = "BOOK-DATA-7f3a"
BASE_URL = "https://testserver"

AppFactory = Callable[..., FastAPI]
ClientFactory = Callable[[FastAPI], TestClient]


def _book_payload() -> dict[str, Any]:
    return {"marker": BOOK_MARKER, "total": "1234.56", "account": "Bank"}


def dummy_book_routers() -> list[APIRouter]:
    journal = APIRouter(prefix="/api/journal")
    ledger = APIRouter(prefix="/api/ledger")
    reports = APIRouter(prefix="/api/reports")
    settings = APIRouter(prefix="/api/settings")
    documents = APIRouter(prefix="/api/documents")

    @journal.get("")
    async def journal_list() -> dict[str, Any]:
        return _book_payload()

    @journal.get("/{entry_id}")
    async def journal_entry(entry_id: int) -> dict[str, Any]:
        return _book_payload()

    @ledger.get("/{account_id}")
    async def ledger_account(account_id: int) -> dict[str, Any]:
        return _book_payload()

    @reports.get("/trial-balance")
    async def trial_balance() -> dict[str, Any]:
        return _book_payload()

    @reports.get("/profit-and-loss")
    async def profit_and_loss() -> dict[str, Any]:
        return _book_payload()

    @settings.get("")
    async def settings_get() -> dict[str, Any]:
        return _book_payload()

    @settings.put("")
    async def settings_put() -> dict[str, Any]:
        return _book_payload()

    @documents.get("/{document_id}/file")
    async def document_file(document_id: int) -> dict[str, Any]:
        return _book_payload()

    return [journal, ledger, reports, settings, documents]


DUMMY_PROTECTED_PATHS: frozenset[str] = frozenset(
    {
        "/api/journal",
        "/api/journal/{entry_id}",
        "/api/ledger/{account_id}",
        "/api/reports/trial-balance",
        "/api/reports/profit-and-loss",
        "/api/settings",
        "/api/documents/{document_id}/file",
    }
)


@pytest.fixture
def make_app(database_url: str) -> AppFactory:
    def _make(**overrides: Any) -> FastAPI:
        settings = load_settings(database_url=database_url, **overrides)
        app = create_app(settings)
        for router in dummy_book_routers():
            include_protected(app, router)
        return app

    return _make


@pytest.fixture
def make_client() -> Iterator[ClientFactory]:
    with ExitStack() as stack:

        def _make(app: FastAPI) -> TestClient:
            client = TestClient(app, base_url=BASE_URL, follow_redirects=False)
            return stack.enter_context(client)

        yield _make


def forge_session_cookie(secret: str, session: dict[str, Any]) -> str:
    data = b64encode(json.dumps(session).encode("utf-8"))
    return TimestampSigner(secret).sign(data).decode("utf-8")


def set_session_cookie(client: TestClient, value: str) -> None:
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, value, domain="testserver")
