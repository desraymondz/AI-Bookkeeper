"""See planning/04-test-spec.md F-007.1 (T-065, T-066 are browser tests over this API)."""

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.factories import account, seeded_chart


@pytest.fixture
async def seafood(db_session: AsyncSession) -> int:
    await seeded_chart(db_session)
    return (await account(db_session, "COGS Seafood")).id


async def test_add_supplier_with_optional_fields(client: httpx.AsyncClient, seafood: int) -> None:
    res = await client.post(
        "/api/suppliers",
        json={
            "name": "Ocean Fresh",
            "default_account_id": seafood,
            "uen": "201912345K",
            "terms_days": 30,
            "telegram_username_hint": "@oceanfresh",
        },
    )

    assert res.status_code == 201
    body = res.json()
    assert (body["name"], body["active"], body["default_account_name"]) == (
        "Ocean Fresh",
        True,
        "COGS Seafood",
    )
    assert [r["name"] for r in (await client.get("/api/suppliers")).json()] == ["Ocean Fresh"]


async def test_blank_uen_and_hint_are_stored_as_none(
    client: httpx.AsyncClient, seafood: int
) -> None:
    res = await client.post(
        "/api/suppliers",
        json={
            "name": "Dairy Best",
            "default_account_id": seafood,
            "uen": "",
            "telegram_username_hint": " ",
        },
    )

    assert res.status_code == 201
    assert (res.json()["uen"], res.json()["telegram_username_hint"]) == (None, None)


@pytest.mark.parametrize("name", ["", "   "])
async def test_name_and_account_are_required(
    client: httpx.AsyncClient, seafood: int, name: str
) -> None:
    empty_name = await client.post(
        "/api/suppliers", json={"name": name, "default_account_id": seafood}
    )
    no_account = await client.post("/api/suppliers", json={"name": "X"})
    bad_account = await client.post(
        "/api/suppliers", json={"name": "X", "default_account_id": 99999}
    )

    assert {empty_name.status_code, no_account.status_code, bad_account.status_code} == {422}
    assert (await client.get("/api/suppliers")).json() == []


async def test_update_and_deactivate(client: httpx.AsyncClient, seafood: int) -> None:
    created = (
        await client.post(
            "/api/suppliers", json={"name": "Ocean Fresh", "default_account_id": seafood}
        )
    ).json()

    res = await client.patch(
        f"/api/suppliers/{created['id']}", json={"active": False, "terms_days": 14}
    )

    assert (res.json()["active"], res.json()["terms_days"]) == (False, 14)
    assert (await client.patch("/api/suppliers/99999", json={"active": False})).status_code == 404
