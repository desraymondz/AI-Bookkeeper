"""See planning/decisions.md#D-031."""

import datetime as dt

import httpx
import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update

from bookkeeper.agents.llm import LLMClient, LLMPart, LLMResult
from bookkeeper.main import create_app
from bookkeeper.routes import PROTECTED_ROUTERS, PUBLIC_ROUTERS
from tests.support import telegram_updates as tu
from tests.support.factories import account, demo_cafe, post, seeded_chart, settings_row, supplier
from tests.support.fakes import FakeLLMClient, RecordingBot


def test_registry_registers_every_router_once() -> None:
    app = create_app()
    included = [getattr(route, "original_router", None) for route in app.routes]
    routers = [*PUBLIC_ROUTERS, *PROTECTED_ROUTERS]
    for router in routers:
        assert sum(1 for item in included if item is router) == 1
    assert len({id(router) for router in routers}) == len(routers)


async def test_protected_routers_reject_anonymous(anon_client: httpx.AsyncClient) -> None:
    checked = 0
    for router in PROTECTED_ROUTERS:
        for route in router.routes:
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", None) or set()
            if "{" in path or "GET" not in methods:
                continue
            res = await anon_client.get(path)
            assert res.status_code == 401, path
            checked += 1
    assert checked > 0


async def test_signed_in_client_reaches_protected_routes(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/settings")).status_code == 200


async def test_fake_llm_records_calls_and_plays_queue() -> None:
    class Out(BaseModel):
        value: int

    fake = FakeLLMClient()
    llm: LLMClient = fake
    fake.queue("extract", LLMResult(parsed=Out(value=1), model="m"))
    fake.set_default("router", LLMResult(text="hi", model="m"))

    first = await llm.generate(
        task="extract", system="sys", parts=[LLMPart.from_text("a")], schema=Out
    )
    second = await llm.generate(task="router", system="s", parts=[], schema=None)

    assert first.parsed == Out(value=1)
    assert second.text == "hi"
    assert [c.task for c in fake.calls] == ["extract", "router"]
    assert fake.calls_for("extract")[0].parts[0].text == "a"
    with pytest.raises(AssertionError):
        await llm.generate(task="extract", system="s", parts=[], schema=None)


async def test_recording_bot_records_calls() -> None:
    bot = RecordingBot(files={"f1": b"data"})
    sent = await bot.send_message(5, "hello", reply_markup={"k": 1})
    await bot.send_document(5, b"x", caption="doc")
    await bot.send_photo(5, b"y", caption="pic")
    edited = await bot.edit_message_text("new", chat_id=5, message_id=sent.message_id)
    await bot.edit_message_reply_markup(chat_id=5, message_id=sent.message_id, reply_markup=None)
    assert await bot.answer_callback_query("cb", text="ok") is True
    file = await bot.get_file("f1")

    assert isinstance(sent.message_id, int)
    assert edited.message_id == sent.message_id
    assert bot.sent_texts == ["hello"]
    assert bot.calls[0].chat_id == 5
    assert bot.calls[0].reply_markup == {"k": 1}
    assert [c.method for c in bot.calls] == [
        "send_message",
        "send_document",
        "send_photo",
        "edit_message_text",
        "edit_message_reply_markup",
        "answer_callback_query",
        "get_file",
    ]
    assert bytes(await file.download_as_bytearray()) == b"data"


def test_update_builders_parse_as_telegram_updates() -> None:
    cases = {
        "text": tu.text_message(11, "hello", "ann"),
        "start": tu.start_command(11, "tok123", "ann"),
        "pdf": tu.document_message(11, "inv.pdf"),
        "xlsx": tu.document_message(11, "sales.xlsx"),
        "photo": tu.photo_message(11),
        "callback": tu.callback_query(11, "approve:1"),
    }
    parsed = {name: Update.de_json(data, bot=None) for name, data in cases.items()}

    assert parsed["text"].message is not None
    assert parsed["text"].message.text == "hello"
    assert parsed["text"].effective_user is not None
    assert parsed["text"].effective_user.id == 11
    assert parsed["text"].effective_user.username == "ann"
    assert parsed["start"].message is not None
    assert parsed["start"].message.text == "/start tok123"
    assert parsed["start"].message.entities[0].type == "bot_command"
    assert parsed["pdf"].message is not None
    assert parsed["pdf"].message.document is not None
    assert parsed["pdf"].message.document.mime_type == tu.PDF_MIME
    assert parsed["xlsx"].message is not None
    assert parsed["xlsx"].message.document is not None
    assert parsed["xlsx"].message.document.mime_type == tu.XLSX_MIME
    assert parsed["photo"].message is not None
    assert len(parsed["photo"].message.photo) == 2
    assert parsed["callback"].callback_query is not None
    assert parsed["callback"].callback_query.data == "approve:1"
    assert parsed["callback"].callback_query.from_user.id == 11


async def test_factories_build_posted_books(db_session: AsyncSession) -> None:
    await seeded_chart(db_session)
    await settings_row(db_session, name="Kopi Corner")
    cogs = await account(db_session, "5000")
    row = await supplier(db_session, "Ocean Fresh", cogs, terms_days=14)
    entry = await post(
        db_session,
        dt.date(2026, 11, 1),
        [("1000", "10.00", "0"), ("4000", "0", "10.00")],
    )
    assert row.terms_days == 14
    assert entry.entry_no is not None


async def test_demo_cafe_seeds_empty_database(db_session: AsyncSession) -> None:
    summary = await demo_cafe(db_session)
    assert summary.entries > 0
