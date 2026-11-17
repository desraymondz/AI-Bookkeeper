import os
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from tests.env import DUMMY_ENV

os.environ.update(DUMMY_ENV)
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

from bookkeeper.db.session import create_engine

pytest_plugins = ["tests.support.app", "tests.support.factories", "tests.support.fakes"]

API_DIR = Path(__file__).resolve().parents[1]
PG_IMAGE = "pgvector/pgvector:0.8.7-pg18-trixie"


def _migrate(url: str) -> None:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")


def _fresh_database(base_url: str) -> Iterator[str]:
    base = make_url(base_url)
    name = f"bk_test_{uuid.uuid4().hex[:12]}"
    admin = create_sync_engine(base, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = base.set(database=name).render_as_string(hide_password=False)
    try:
        _migrate(url)
        yield url
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """See planning/03-tech-stack.md#12-testing-strategy."""
    external = os.environ.get("TEST_DATABASE_URL")
    if external:
        yield from _fresh_database(external)
        return

    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer(PG_IMAGE, driver="psycopg") as pg:
        url: str = pg.get_connection_url()
        _migrate(url)
        yield url


@pytest.fixture
async def db_engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(database_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with db_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
