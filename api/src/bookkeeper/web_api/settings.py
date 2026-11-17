"""See planning/01-prd.md#f-002-first-run-setup-and-business-settings-web."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.settings_service import (
    SettingsData,
    SettingsInput,
    get_settings,
    save_settings,
)
from bookkeeper.web_api import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])

Db = Annotated[AsyncSession, Depends(get_db)]


class SettingsDefaults(SettingsInput):
    name: str = ""


class SettingsState(BaseModel):
    configured: bool
    settings: SettingsData | None
    defaults: SettingsDefaults


@router.get("", response_model=SettingsState)
async def read_settings(session: Db) -> SettingsState:
    current = await get_settings(session)
    return SettingsState(
        configured=current is not None,
        settings=current,
        defaults=SettingsDefaults(),
    )


@router.put("", response_model=SettingsData)
async def write_settings(body: SettingsInput, session: Db) -> SettingsData:
    return await save_settings(session, body)
