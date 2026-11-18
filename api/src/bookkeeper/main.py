import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bookkeeper.agents import services
from bookkeeper.auth.wiring import install_auth
from bookkeeper.config import ConfigError, Settings, get_settings
from bookkeeper.db.session import create_engine, create_sessionmaker
from bookkeeper.routes import register_routes
from bookkeeper.telegram.app import drain


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings if settings is not None else get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # See planning/03-tech-stack.md#1-architecture-at-a-glance and section 6
        engine = create_engine(resolved.database_url)
        app.state.engine = engine
        app.state.sessionmaker = create_sessionmaker(engine)
        try:
            yield
        finally:
            await drain(app)
            await services.close()
            await engine.dispose()

    app = FastAPI(title="AI Bookkeeper", lifespan=lifespan)
    app.state.settings = resolved
    install_auth(app, resolved)
    register_routes(app)
    return app


def _app_or_exit() -> FastAPI:
    try:
        return create_app()
    except ConfigError as exc:
        print(f"AI Bookkeeper cannot start.\n{exc}", file=sys.stderr)
        raise SystemExit(1) from exc


app = _app_or_exit()
