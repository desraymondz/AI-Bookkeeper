from fastapi import APIRouter, FastAPI

from bookkeeper.auth.wiring import include_protected
from bookkeeper.telegram import webhook as telegram_webhook
from bookkeeper.telegram.handlers import supplier_docs
from bookkeeper.web_api import accounts as accounts_api
from bookkeeper.web_api import config as config_api
from bookkeeper.web_api import documents as documents_api
from bookkeeper.web_api import ledger as ledger_api
from bookkeeper.web_api import reports as reports_api
from bookkeeper.web_api import settings as settings_api

# See planning/decisions.md#D-031
PUBLIC_ROUTERS: list[APIRouter] = [
    config_api.router,
    telegram_webhook.router,
]

PROTECTED_ROUTERS: list[APIRouter] = [
    settings_api.router,
    accounts_api.router,
    reports_api.router,
    ledger_api.router,
    documents_api.router,
]

HANDLER_MODULES = [supplier_docs]


def register_protected(app: FastAPI, routers: list[APIRouter]) -> None:
    for router in routers:
        include_protected(app, router)


def register_routes(app: FastAPI) -> None:
    for router in PUBLIC_ROUTERS:
        app.include_router(router)
    register_protected(app, PROTECTED_ROUTERS)
