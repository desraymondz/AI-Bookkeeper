import httpx
import pytest

from tests.env import DUMMY_ENV

pytestmark = pytest.mark.integration


async def test_config_before_setup(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/config")

    assert res.status_code == 200
    assert res.json() == {
        "bot_username": DUMMY_ENV["TELEGRAM_BOT_USERNAME"],
        "business_name": None,
    }


async def test_config_after_setup(client: httpx.AsyncClient) -> None:
    await client.put("/api/settings", json={"name": "Kopi Corner"})

    res = await client.get("/api/config")

    assert res.json()["business_name"] == "Kopi Corner"
