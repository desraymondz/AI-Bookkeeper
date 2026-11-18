"""LLM client and checkpointer. See planning/03-tech-stack.md#5-langgraph-layout."""

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncEngine

from bookkeeper.agents.gemini import GeminiClient
from bookkeeper.agents.llm import LLMClient
from bookkeeper.config import Settings
from bookkeeper.db.session import create_engine, create_sessionmaker

CHECKPOINT_SCHEMA = "langgraph"

_llm: LLMClient | None = None
_checkpointer: BaseCheckpointSaver[Any] | None = None
_checkpointer_manager: AbstractAsyncContextManager[AsyncPostgresSaver] | None = None
_engine: AsyncEngine | None = None
_override_llm: LLMClient | None = None
_override_checkpointer: BaseCheckpointSaver[Any] | None = None


def libpq_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def llm_for(settings: Settings) -> LLMClient:
    global _llm, _engine
    if _override_llm is not None:
        return _override_llm
    if _llm is None:
        _engine = create_engine(settings.database_url)
        sessionmaker = create_sessionmaker(_engine)
        _llm = GeminiClient(settings, audit_sessionmaker=sessionmaker)
    return _llm


@asynccontextmanager
async def open_checkpointer(database_url: str) -> AsyncIterator[AsyncPostgresSaver]:
    pool: AsyncConnectionPool[Any] = AsyncConnectionPool(
        libpq_url(database_url),
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
            "options": f"-c search_path={CHECKPOINT_SCHEMA}",
        },
        open=False,
    )
    await pool.open()
    try:
        async with pool.connection() as conn:
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {CHECKPOINT_SCHEMA}")
        saver = AsyncPostgresSaver(pool)
        await saver.setup()
        yield saver
    finally:
        await pool.close()


async def checkpointer_for(settings: Settings) -> BaseCheckpointSaver[Any]:
    global _checkpointer, _checkpointer_manager
    if _override_checkpointer is not None:
        return _override_checkpointer
    if _checkpointer is None:
        manager = open_checkpointer(settings.database_url)
        _checkpointer = await manager.__aenter__()
        _checkpointer_manager = manager
    return _checkpointer


async def close() -> None:
    """Release the pool, LLM client and engine. See planning/build-plan.md (P2-T10)."""
    global _llm, _checkpointer, _checkpointer_manager, _engine
    manager, llm, engine = _checkpointer_manager, _llm, _engine
    _llm, _checkpointer, _checkpointer_manager, _engine = None, None, None, None
    try:
        if manager is not None:
            await manager.__aexit__(None, None, None)
    finally:
        try:
            if isinstance(llm, GeminiClient):
                await llm.aclose()
        finally:
            if engine is not None:
                await engine.dispose()


@asynccontextmanager
async def override(
    *, llm: LLMClient | None = None, checkpointer: BaseCheckpointSaver[Any] | None = None
) -> AsyncIterator[None]:
    global _override_llm, _override_checkpointer
    saved = (_override_llm, _override_checkpointer)
    _override_llm, _override_checkpointer = llm, checkpointer
    try:
        yield
    finally:
        _override_llm, _override_checkpointer = saved
