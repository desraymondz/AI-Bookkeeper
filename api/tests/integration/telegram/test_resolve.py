from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.telegram.conftest import BOSS_ID, DEACTIVATED_ID, STRANGER_ID, SUPPLIER_ID

from bookkeeper.db.models import Supplier
from bookkeeper.telegram.router import Role, resolve_sender


async def test_resolve_sender_roles(
    db_session: AsyncSession, people: dict[str, Supplier | None]
) -> None:
    roles = {
        uid: (await resolve_sender(db_session, uid)).role
        for uid in (BOSS_ID, SUPPLIER_ID, DEACTIVATED_ID, STRANGER_ID)
    }
    assert roles == {
        BOSS_ID: Role.BOSS,
        SUPPLIER_ID: Role.SUPPLIER,
        DEACTIVATED_ID: Role.STRANGER,
        STRANGER_ID: Role.STRANGER,
    }
