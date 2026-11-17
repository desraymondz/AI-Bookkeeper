"""T-075 and the users list, change supplier and revoke paths of F-008.2."""

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Supplier, User, UserRole, UserStatus
from tests.support.factories import seeded_chart, supplier


@pytest.fixture
async def team(db_session: AsyncSession) -> dict[str, User | Supplier]:
    await seeded_chart(db_session)
    ocean = await supplier(db_session, "Ocean Fresh", "5000")
    dairy = await supplier(db_session, "Dairy Best", "5010")
    boss = User(telegram_user_id=1, username="boss", role=UserRole.BOSS)
    owner = User(telegram_user_id=2, username="oc", role=UserRole.SUPPLIER, supplier_id=ocean.id)
    db_session.add_all([boss, owner])
    await db_session.flush()
    return {"boss": boss, "user": owner, "ocean": ocean, "dairy": dairy}


async def _active_bosses(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.BOSS, User.status == UserStatus.ACTIVE)
        )
        or 0
    )


async def test_t075_boss_cannot_be_deactivated_duplicated_or_promoted_to(
    client: httpx.AsyncClient, db_session: AsyncSession, team: dict[str, User | Supplier]
) -> None:
    boss, owner = team["boss"], team["user"]

    deactivate = await client.patch(f"/api/users/{boss.id}", json={"status": "deactivated"})
    add_boss = await client.post("/api/users", json={"role": "boss"})
    promote = await client.patch(f"/api/users/{owner.id}", json={"role": "boss"})
    revoke = await client.post(f"/api/users/{boss.id}/revoke")

    assert deactivate.status_code == 409
    assert add_boss.status_code in {404, 405}
    assert promote.status_code == 409
    assert revoke.status_code == 409
    assert await _active_bosses(db_session) == 1


async def test_list_shows_role_supplier_and_status(
    client: httpx.AsyncClient, team: dict[str, User | Supplier]
) -> None:
    rows = (await client.get("/api/users")).json()

    assert [(r["role"], r["supplier_name"], r["status"]) for r in rows] == [
        ("boss", None, "active"),
        ("supplier", "Ocean Fresh", "active"),
    ]


async def test_change_linked_supplier_and_revoke(
    client: httpx.AsyncClient, db_session: AsyncSession, team: dict[str, User | Supplier]
) -> None:
    owner, dairy = team["user"], team["dairy"]

    changed = await client.patch(f"/api/users/{owner.id}", json={"supplier_id": dairy.id})
    assert changed.json()["supplier_name"] == "Dairy Best"
    bad = await client.patch(f"/api/users/{owner.id}", json={"supplier_id": 99999})
    assert bad.status_code == 422

    revoked = await client.post(f"/api/users/{owner.id}/revoke")
    assert revoked.json()["status"] == "deactivated"
    refreshed = await db_session.get_one(User, owner.id)
    assert refreshed.telegram_user_id is None
