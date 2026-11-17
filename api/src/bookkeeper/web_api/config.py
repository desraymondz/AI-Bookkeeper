"""See planning/decisions.md#D-027."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.config import Settings
from bookkeeper.settings_service import get_settings
from bookkeeper.web_api import get_db

router = APIRouter(prefix="/api", tags=["config"])


class PublicConfig(BaseModel):
    bot_username: str | None
    business_name: str | None


@router.get("/config", response_model=PublicConfig)
async def read_config(
    request: Request, session: Annotated[AsyncSession, Depends(get_db)]
) -> PublicConfig:
    env: Settings = request.app.state.settings
    current = await get_settings(session)
    return PublicConfig(
        bot_username=env.telegram_bot_username or None,
        business_name=current.name if current is not None else None,
    )
