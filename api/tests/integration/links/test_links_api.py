"""T-058."""

import datetime as dt

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper import linking
from tests.support.factories import seeded_chart, supplier


@pytest.fixture
def frozen_now(monkeypatch: pytest.MonkeyPatch) -> dt.datetime:
    moment = dt.datetime(2026, 11, 18, 13, 0, tzinfo=dt.UTC)
    monkeypatch.setattr(linking, "utcnow", lambda: moment)
    return moment


async def test_t058_boss_token_expires_in_24_hours(
    client: httpx.AsyncClient, frozen_now: dt.datetime
) -> None:
    res = await client.post("/api/links/boss")

    assert res.status_code == 201
    body = res.json()
    assert dt.datetime.fromisoformat(body["expires_at"]) == dt.datetime(
        2026, 11, 19, 13, 0, tzinfo=dt.UTC
    )
    assert body["url"] == f"https://t.me/{_bot_username(client)}?start={body['token']}"


def _bot_username(client: httpx.AsyncClient) -> str:
    from tests.support.app import app_of

    return str(app_of(client).state.settings.telegram_bot_username)


async def test_t058_token_is_single_use(
    client: httpx.AsyncClient, db_session: AsyncSession, frozen_now: dt.datetime
) -> None:
    token = (await client.post("/api/links/boss")).json()["token"]

    first = await linking.redeem(
        db_session, token, telegram_user_id=11, username="a", display_name="A"
    )
    second = await linking.redeem(
        db_session, token, telegram_user_id=12, username="b", display_name="B"
    )

    assert first.outcome is linking.Outcome.BOSS_LINKED
    assert second.outcome is linking.Outcome.INVALID


async def test_supplier_invite_lasts_seven_days(
    client: httpx.AsyncClient, db_session: AsyncSession, frozen_now: dt.datetime
) -> None:
    await seeded_chart(db_session)
    ocean = await supplier(db_session, "Ocean Fresh", "5000")

    res = await client.post(f"/api/links/suppliers/{ocean.id}")

    assert res.status_code == 201
    assert dt.datetime.fromisoformat(res.json()["expires_at"]) == dt.datetime(
        2026, 11, 25, 13, 0, tzinfo=dt.UTC
    )


async def test_invite_refused_for_inactive_or_missing_supplier(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await seeded_chart(db_session)
    old = await supplier(db_session, "Old Dairy", "5010", active=False)

    assert (await client.post(f"/api/links/suppliers/{old.id}")).status_code == 409
    assert (await client.post("/api/links/suppliers/99999")).status_code == 404
