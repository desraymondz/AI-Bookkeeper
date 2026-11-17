"""T-059, T-060, T-061, T-062, T-064, T-068, T-069, T-070, T-076."""

import datetime as dt

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.telegram.conftest import post_update
from tests.support import telegram_updates as tu
from tests.support.factories import seeded_chart, supplier
from tests.support.fakes import RecordingBot

from bookkeeper import linking
from bookkeeper.db.models import LinkPurpose, Supplier, User, UserRole, UserStatus
from bookkeeper.telegram.router import Role, resolve_sender

BOSS_A = 7001
BOSS_B = 7002
VISITOR = 7003
SUPPLIER_USER = 7004
NEUTRAL = "This link is not valid or has expired."


@pytest.fixture
async def ocean(db_session: AsyncSession) -> Supplier:
    await seeded_chart(db_session)
    return await supplier(db_session, "Ocean Fresh", "5000")


async def _boss_token(session: AsyncSession, now: dt.datetime | None = None) -> str:
    token, _ = await linking.create_token(session, LinkPurpose.BOSS, now=now)
    return token


async def _users(session: AsyncSession) -> list[User]:
    return list((await session.scalars(select(User).order_by(User.id))).all())


async def test_t059_boss_token_binds_telegram_user(
    client: httpx.AsyncClient, tg_app: FastAPI, bot: RecordingBot, db_session: AsyncSession
) -> None:
    token = await _boss_token(db_session)

    await post_update(client, tg_app, tu.start_command(BOSS_A, token, username="boss_a"))

    users = await _users(db_session)
    assert [(u.role, u.telegram_user_id, u.username) for u in users] == [
        (UserRole.BOSS, BOSS_A, "boss_a")
    ]
    assert bot.sent_texts == ["Connected. This chat is now the boss chat."]
    state = (await client.get("/api/links/boss")).json()
    assert state["connected"] is True
    assert state["username"] == "boss_a"


@pytest.mark.parametrize("age_hours", [25])
async def test_t060_expired_boss_token_binds_nothing(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    db_session: AsyncSession,
    age_hours: int,
) -> None:
    created = linking.utcnow() - dt.timedelta(hours=age_hours)
    token = await _boss_token(db_session, created)

    await post_update(client, tg_app, tu.start_command(BOSS_A, token))

    assert await _users(db_session) == []
    assert bot.sent_texts == [NEUTRAL]


async def test_t061_used_boss_token_leaves_binding(
    client: httpx.AsyncClient, tg_app: FastAPI, bot: RecordingBot, db_session: AsyncSession
) -> None:
    token = await _boss_token(db_session)
    await post_update(client, tg_app, tu.start_command(BOSS_A, token))
    bot.calls.clear()

    await post_update(client, tg_app, tu.start_command(VISITOR, token))

    assert [(u.role, u.telegram_user_id) for u in await _users(db_session)] == [
        (UserRole.BOSS, BOSS_A)
    ]
    assert bot.sent_texts == [NEUTRAL]


async def test_t062_unknown_token_reveals_nothing(
    client: httpx.AsyncClient, tg_app: FastAPI, bot: RecordingBot, db_session: AsyncSession
) -> None:
    await post_update(client, tg_app, tu.start_command(VISITOR, "not-a-real-token"))

    assert await _users(db_session) == []
    assert bot.sent_texts == [NEUTRAL]


async def test_t064_reconnect_turns_old_account_into_stranger(
    client: httpx.AsyncClient, tg_app: FastAPI, bot: RecordingBot, db_session: AsyncSession
) -> None:
    await post_update(
        client, tg_app, tu.start_command(BOSS_A, await _boss_token(db_session), username="a")
    )
    await post_update(
        client, tg_app, tu.start_command(BOSS_B, await _boss_token(db_session), username="b")
    )

    users = await _users(db_session)
    assert [(u.role, u.telegram_user_id, u.status) for u in users] == [
        (UserRole.BOSS, BOSS_B, UserStatus.ACTIVE)
    ]
    assert (await resolve_sender(db_session, BOSS_A)).role is Role.STRANGER
    assert (await resolve_sender(db_session, BOSS_B)).role is Role.BOSS

    bot.calls.clear()
    await post_update(client, tg_app, tu.callback_query(BOSS_A, "approve:1"))
    assert bot.calls_for("send_message") == []


async def test_t068_supplier_invite_binds_and_tells_boss(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    db_session: AsyncSession,
    ocean: Supplier,
) -> None:
    await post_update(
        client, tg_app, tu.start_command(BOSS_A, await _boss_token(db_session), username="a")
    )
    token, _ = await linking.create_token(db_session, LinkPurpose.SUPPLIER, supplier_id=ocean.id)
    bot.calls.clear()

    await post_update(client, tg_app, tu.start_command(SUPPLIER_USER, token, username="oceanfresh"))

    sender = await resolve_sender(db_session, SUPPLIER_USER)
    assert (sender.role, sender.supplier_id) == (Role.SUPPLIER, ocean.id)
    by_chat = {c.chat_id: c.text for c in bot.calls_for("send_message")}
    assert "Ocean Fresh" in (by_chat[SUPPLIER_USER] or "")
    assert "Ocean Fresh" in (by_chat[BOSS_A] or "")


@pytest.mark.parametrize("scenario", ["old", "used"])
async def test_t069_stale_supplier_invite_binds_nothing(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    db_session: AsyncSession,
    ocean: Supplier,
    scenario: str,
) -> None:
    created = linking.utcnow() - dt.timedelta(days=8 if scenario == "old" else 0)
    token, _ = await linking.create_token(
        db_session, LinkPurpose.SUPPLIER, supplier_id=ocean.id, now=created
    )
    if scenario == "used":
        await post_update(client, tg_app, tu.start_command(SUPPLIER_USER, token))
        bot.calls.clear()

    await post_update(client, tg_app, tu.start_command(VISITOR, token))

    assert (await resolve_sender(db_session, VISITOR)).role is Role.STRANGER
    assert bot.sent_texts == [NEUTRAL]


async def test_t070_deactivated_supplier_is_a_stranger(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    db_session: AsyncSession,
    ocean: Supplier,
) -> None:
    token, _ = await linking.create_token(db_session, LinkPurpose.SUPPLIER, supplier_id=ocean.id)
    await post_update(client, tg_app, tu.start_command(SUPPLIER_USER, token))
    assert (await resolve_sender(db_session, SUPPLIER_USER)).role is Role.SUPPLIER

    res = await client.patch(f"/api/suppliers/{ocean.id}", json={"active": False})

    assert res.status_code == 200
    assert (await resolve_sender(db_session, SUPPLIER_USER)).role is Role.STRANGER


async def test_t076_supplier_questions_get_fixed_reply(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    db_session: AsyncSession,
    ocean: Supplier,
) -> None:
    await supplier(db_session, "Dairy Best", "5010")
    token, _ = await linking.create_token(db_session, LinkPurpose.SUPPLIER, supplier_id=ocean.id)
    await post_update(client, tg_app, tu.start_command(SUPPLIER_USER, token))
    bot.calls.clear()

    for question in ("how much do you owe us?", "what does Dairy Best charge you?"):
        await post_update(client, tg_app, tu.text_message(SUPPLIER_USER, question))

    assert len(bot.sent_texts) == 2
    for text in bot.sent_texts:
        assert "Dairy Best" not in text
        assert not any(ch.isdigit() for ch in text)
