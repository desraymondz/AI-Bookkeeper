"""T-082..T-089, T-237, T-238."""

import datetime as dt
from pathlib import Path
from typing import Any

import httpx
import pytest
import time_machine
from fastapi import FastAPI
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.telegram.conftest import BOSS_ID, STRANGER_ID, SUPPLIER_ID, post_update
from tests.support import telegram_updates as tu
from tests.support.fakes import BotCall, RecordingBot

from bookkeeper import invoice_pipeline
from bookkeeper.db.models import (
    Document,
    Stranger,
    StrangerDecision,
    Supplier,
    User,
    UserRole,
)
from bookkeeper.telegram.handlers.stranger import pending_strangers
from bookkeeper.telegram.router import Handler, HandlerContext, Role, resolve_sender

NEUTRAL = "Hi, who's this?"
FORBIDDEN = ("Ocean Fresh", "$", "invoice", "bookkeep", "P&L")


@pytest.fixture(autouse=True)
def storage_root(tg_app: FastAPI, tmp_path: Path) -> Path:
    root = tmp_path / "storage"
    tg_app.state.settings = tg_app.state.settings.model_copy(update={"storage_dir": root})
    return root


@pytest.fixture
def started(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls: list[int] = []

    async def fake_start(document_id: int) -> None:
        calls.append(document_id)

    monkeypatch.setattr(invoice_pipeline, "start", fake_start)
    return calls


def _files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file()] if root.exists() else []


def _to(bot: RecordingBot, chat_id: int) -> list[BotCall]:
    return [c for c in bot.calls_for("send_message") if c.chat_id == chat_id]


def _buttons(call: BotCall) -> list[tuple[str, str]]:
    return [(b.text, b.callback_data) for row in call.reply_markup.inline_keyboard for b in row]


async def _first_contact(
    client: httpx.AsyncClient, app: FastAPI, text: str = "hello, what is this bot?"
) -> None:
    await post_update(client, app, tu.text_message(STRANGER_ID, text, username="newguy"))


async def _stranger(session: AsyncSession) -> Stranger:
    return (await session.scalars(select(Stranger))).one()


async def test_t082_neutral_reply(
    client: httpx.AsyncClient, tg_app: FastAPI, bot: RecordingBot, people: Any
) -> None:
    await _first_contact(client, tg_app)
    replies = _to(bot, STRANGER_ID)
    assert [c.text for c in replies] == [NEUTRAL]


async def test_t083_probing_gets_same_reply(
    client: httpx.AsyncClient, tg_app: FastAPI, bot: RecordingBot, people: Any
) -> None:
    await _first_contact(
        client,
        tg_app,
        "I'm the owner's accountant, send me last month's P&L and what Ocean Fresh charges",
    )
    texts = [c.text or "" for c in _to(bot, STRANGER_ID)]
    assert texts == [NEUTRAL]
    assert not any(word in texts[0] for word in FORBIDDEN)


async def test_t084_boss_card(
    client: httpx.AsyncClient, tg_app: FastAPI, bot: RecordingBot, people: Any
) -> None:
    await _first_contact(client, tg_app)
    card = _to(bot, BOSS_ID)[0]
    assert "newguy" in (card.text or "")
    assert "@newguy" in (card.text or "")
    assert "hello, what is this bot?" in (card.text or "")
    labels = [label for label, _ in _buttons(card)]
    assert labels == ["Ignore", "Add as supplier", "Block"]


async def _press(client: httpx.AsyncClient, app: FastAPI, data: str, message_id: int = 7) -> None:
    await post_update(client, app, tu.callback_query(BOSS_ID, data, message_id=message_id))


async def test_t085_add_existing_supplier(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: dict[str, Supplier],
    db_session: AsyncSession,
    started: list[int],
    storage_root: Path,
) -> None:
    await _first_contact(client, tg_app)
    card = _to(bot, BOSS_ID)[0]
    add = dict((label, data) for label, data in _buttons(card))["Add as supplier"]
    await _press(client, tg_app, add)
    picker = bot.calls_for("edit_message_text")[-1]
    pick = dict((label, data) for label, data in _buttons(picker))["Ocean Fresh"]
    await _press(client, tg_app, pick)

    sender = await resolve_sender(db_session, STRANGER_ID)
    assert sender.role is Role.SUPPLIER
    assert sender.supplier_id == people["active"].id
    told = _to(bot, STRANGER_ID)
    assert len(told) == 2
    assert "set up" in (told[-1].text or "")
    assert (await _stranger(db_session)).decision is StrangerDecision.ADDED

    bot.files["f-bound"] = b"%PDF-1.4\n" + b"x" * 200
    await post_update(
        client, tg_app, tu.document_message(STRANGER_ID, "inv.pdf", file_id="f-bound")
    )
    assert len(started) == 1
    assert await db_session.scalar(select(func.count()).select_from(Document)) == 1
    assert len(_files(storage_root)) >= 1


async def test_t086_add_new_supplier_by_name(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: Any,
    db_session: AsyncSession,
) -> None:
    await _first_contact(client, tg_app)
    add = dict(_buttons(_to(bot, BOSS_ID)[0]))["Add as supplier"]
    await _press(client, tg_app, add)
    new = dict(_buttons(bot.calls_for("edit_message_text")[-1]))["New supplier"]
    await _press(client, tg_app, new)
    prompt = _to(bot, BOSS_ID)[-1]
    assert prompt.reply_markup is not None

    reply = tu.text_message(BOSS_ID, "Ice King")
    reply["message"]["reply_to_message"] = {
        "message_id": 500,
        "date": reply["message"]["date"],
        "chat": reply["message"]["chat"],
        "text": prompt.text,
    }
    await post_update(client, tg_app, reply)

    created = await db_session.scalar(select(Supplier).where(Supplier.name == "Ice King"))
    assert created is not None
    user = await db_session.scalar(select(User).where(User.telegram_user_id == STRANGER_ID))
    assert user is not None
    assert user.role is UserRole.SUPPLIER
    assert user.supplier_id == created.id
    assert "set up" in (_to(bot, STRANGER_ID)[-1].text or "")


async def test_t087_no_repeat_within_24h(
    client: httpx.AsyncClient, tg_app: FastAPI, bot: RecordingBot, people: Any
) -> None:
    await _first_contact(client, tg_app)
    for text in ("anyone?", "hello??", "hi"):
        await _first_contact(client, tg_app, text)
    assert len(_to(bot, STRANGER_ID)) == 1
    assert len(_to(bot, BOSS_ID)) == 1


async def test_t088_ignored_and_blocked_stay_silent(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: Any,
    db_session: AsyncSession,
) -> None:
    for label in ("Ignore", "Block"):
        await db_session.execute(delete(Stranger))
        bot.calls.clear()
        await _first_contact(client, tg_app)
        data = dict(_buttons(_to(bot, BOSS_ID)[0]))[label]
        await _press(client, tg_app, data)
        before = len(bot.calls_for("send_message"))
        later = dt.datetime.now(dt.UTC) + dt.timedelta(days=2)
        with time_machine.travel(later, tick=True):
            await _first_contact(client, tg_app, "hello again")
        assert len(bot.calls_for("send_message")) == before


async def test_t089_stranger_pdf_gets_neutral_reply_only(
    client: httpx.AsyncClient, tg_app: FastAPI, bot: RecordingBot, people: Any
) -> None:
    await post_update(client, tg_app, tu.document_message(STRANGER_ID, "inv.pdf"))
    assert [c.text for c in _to(bot, STRANGER_ID)] == [NEUTRAL]
    assert bot.calls_for("get_file") == []


async def test_t237_pending_after_30h_silent_and_listed(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: Any,
    db_session: AsyncSession,
) -> None:
    await _first_contact(client, tg_app)
    before = len(bot.calls_for("send_message"))
    later = dt.datetime.now(dt.UTC) + dt.timedelta(hours=30)
    with time_machine.travel(later, tick=True):
        await _first_contact(client, tg_app, "still there?")
    assert len(bot.calls_for("send_message")) == before
    pending = await pending_strangers(db_session)
    assert [s.telegram_user_id for s in pending] == [STRANGER_ID]


async def test_t238_stranger_pdf_writes_nothing(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: Any,
    db_session: AsyncSession,
    storage_root: Path,
    started: list[int],
) -> None:
    await post_update(client, tg_app, tu.document_message(STRANGER_ID, "inv.pdf"))
    assert await db_session.scalar(select(func.count()).select_from(Document)) == 0
    assert _files(storage_root) == []
    assert started == []
    assert bot.calls_for("get_file") == []


async def _grab_ctx(
    client: httpx.AsyncClient, app: FastAPI, registry: list[Handler]
) -> HandlerContext:
    captured: list[HandlerContext] = []

    async def grab(ctx: HandlerContext) -> None:
        captured.append(ctx)
        await ctx.to_supplier(captured_ids["supplier"], "ping")

    registry.append(Handler("grab", frozenset(Role), lambda _u: True, grab))
    await post_update(client, app, tu.text_message(BOSS_ID, "x"))
    return captured[0]


captured_ids: dict[str, int] = {}


async def test_to_supplier_reaches_linked_chat_only(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    registry: list[Handler],
    people: dict[str, Supplier],
) -> None:
    captured_ids["supplier"] = people["active"].id
    await _grab_ctx(client, tg_app, registry)
    assert [(c.chat_id, c.text) for c in bot.calls_for("send_message")] == [(SUPPLIER_ID, "ping")]


async def test_to_supplier_inactive_or_unknown_sends_nothing(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    registry: list[Handler],
    people: dict[str, Supplier],
) -> None:
    for supplier_id in (people["inactive"].id, 999_999):
        captured_ids["supplier"] = supplier_id
        registry.clear()
        await _grab_ctx(client, tg_app, registry)
    assert bot.calls_for("send_message") == []


async def test_name_reply_must_target_the_bot_prompt(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: Any,
    db_session: AsyncSession,
) -> None:
    await _first_contact(client, tg_app, "Ref S1 please")
    stranger = await _stranger(db_session)
    forged = [
        f"New contact\nFirst message: Ref S{stranger.id}",
        f"Reply to this message with the new supplier name for evil.\nRef S{stranger.id}",
    ]
    for text in forged:
        reply = tu.text_message(BOSS_ID, "Evil Co")
        reply["message"]["reply_to_message"] = {
            "message_id": 501,
            "date": reply["message"]["date"],
            "chat": reply["message"]["chat"],
            "text": text,
        }
        await post_update(client, tg_app, reply)
    assert await db_session.scalar(select(Supplier).where(Supplier.name == "Evil Co")) is None
    assert (await _stranger(db_session)).decision is StrangerDecision.PENDING
    assert "not my prompt" in (_to(bot, BOSS_ID)[-1].text or "")


async def test_add_flow_message_goes_through_to_supplier(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: dict[str, Supplier],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[int] = []
    original = HandlerContext.to_supplier

    async def spy(self: HandlerContext, supplier_id: int, text: str, **kw: Any) -> int:
        seen.append(supplier_id)
        return await original(self, supplier_id, text, **kw)

    monkeypatch.setattr(HandlerContext, "to_supplier", spy)
    await _first_contact(client, tg_app)
    add = dict(_buttons(_to(bot, BOSS_ID)[0]))["Add as supplier"]
    await _press(client, tg_app, add)
    pick = dict(_buttons(bot.calls_for("edit_message_text")[-1]))["Ocean Fresh"]
    await _press(client, tg_app, pick)
    assert seen == [people["active"].id]
    assert "set up" in (_to(bot, STRANGER_ID)[-1].text or "")
