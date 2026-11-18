"""Fixtures for the invoice pipeline. See planning/decisions.md#D-031."""

import datetime as dt
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
import time_machine
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.agents import services
from bookkeeper.db.models import Supplier
from tests.integration.invoices.helpers import Env
from tests.integration.telegram.conftest import people
from tests.support.factories import settings_row
from tests.support.fakes import FakeLLMClient, RecordingBot

__all__ = ["people"]

NOW = dt.datetime(2026, 11, 18, 2, 0, tzinfo=dt.UTC)


@pytest.fixture
def frozen_time() -> Iterator[None]:
    with time_machine.travel(NOW, tick=True):
        yield


@pytest.fixture
async def checkpointer(database_url: str, fake_llm: FakeLLMClient) -> AsyncIterator[None]:
    async with (
        services.open_checkpointer(database_url) as saver,
        services.override(llm=fake_llm, checkpointer=saver),
    ):
        yield


@pytest.fixture
async def env(
    checkpointer: None,
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    fake_llm: FakeLLMClient,
    db_session: AsyncSession,
    people: dict[str, Supplier | None],
    frozen_time: None,
    tmp_path: Path,
) -> Env:
    root = tmp_path / "storage"
    tg_app.state.settings = tg_app.state.settings.model_copy(update={"storage_dir": root})
    await settings_row(db_session)
    return Env(client, tg_app, bot, fake_llm, db_session)
