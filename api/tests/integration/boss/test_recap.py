"""T-140, T-167, T-168, T-237."""

import datetime as dt
from decimal import Decimal

import time_machine

from bookkeeper.agents.schemas import ExtractedLine
from bookkeeper.db.models import (
    Bill,
    EntrySource,
    EntryStatus,
    Stranger,
)
from bookkeeper.ledger import EntryDraft, LineDraft, hold_entry
from bookkeeper.telegram.handlers.recap import build_recap
from tests.integration.invoices.conftest import NOW
from tests.integration.invoices.helpers import Env
from tests.integration.telegram.conftest import BOSS_ID, STRANGER_ID, post_update
from tests.support import telegram_updates as tu
from tests.support.factories import account_id
from tests.unit.checks.builders import make_invoice

D = Decimal


def _line(description: str, qty: int, price: str) -> ExtractedLine:
    total = D(price) * qty
    return ExtractedLine(
        description=description, unit=None, qty=D(qty), unit_price=D(price), line_total=total
    )


async def _bill(env: Env, supplier_id: int, amount: str, due: dt.date) -> None:
    env.session.add(Bill(supplier_id=supplier_id, amount=D(amount), due_date=due))
    await env.session.flush()


async def test_t167_recap_lists_each_item(env: Env, people: dict[str, object]) -> None:
    await env.send(make_invoice())
    await env.send(
        make_invoice(
            invoice_no="INV-1050",
            lines=[_line("Squid", 3, "100.00")],
            subtotal=D("300.00"),
            gst=D("27.00"),
            total=D("327.00"),
        )
    )
    await env.send(
        make_invoice(
            invoice_no="INV-1051",
            lines=[_line("Crab", 5, "101.00")],
            subtotal=D("505.00"),
            gst=D("40.00"),
            total=D("545.00"),
        )
    )
    await env.say("sales today 1,850, cash 420, card 1,430", reply=False)
    await env.press(env.buttons()["Confirm"])
    supplier = people["active"]
    assert supplier is not None
    supplier_id = getattr(supplier, "id")  # noqa: B009
    await _bill(env, supplier_id, "120.00", dt.date(2026, 11, 20))
    await _bill(env, supplier_id, "80.00", dt.date(2026, 11, 10))
    env.session.add(Stranger(telegram_user_id=STRANGER_ID, display_name="Mystery Guest"))
    await env.session.flush()

    text = await build_recap(env.session, now=NOW + dt.timedelta(hours=11))
    assert "Recap for 18 Nov 2026" in text
    assert "Invoices logged: 3, total 1,308.00" in text
    assert "Sales booked: 1,850.00" in text
    assert "Pending approvals: 1" in text
    assert "Due in the next 3 days:\nOcean Fresh 120.00, due 20 Nov 2026" in text
    assert "Overdue:\nOcean Fresh 80.00, due 10 Nov 2026" in text
    assert "Strangers waiting: Mystery Guest" in text


async def test_t168_quiet_day_is_one_line(env: Env) -> None:
    text = await build_recap(env.session)
    assert text == "Quiet day, 18 Nov 2026: nothing logged, pending, due or overdue."
    await env.say("/recap", reply=False)
    assert env.to_boss()[-1].text == text


async def test_t140_only_items_older_than_24h_are_listed(env: Env) -> None:
    cash = await account_id(env.session, "Cash")
    rent = await account_id(env.session, "Rent")
    for description, age in (("Old item", 25), ("New item", 2)):
        draft = EntryDraft(
            date=dt.date(2026, 11, 17),
            description=description,
            lines=[LineDraft(rent, D("10.00")), LineDraft(cash, credit=D("10.00"))],
            source=EntrySource.AUTO,
        )
        entry = await hold_entry(env.session, draft)
        entry.created_at = NOW - dt.timedelta(hours=age)
        await env.session.flush()
    text = await build_recap(env.session, now=NOW)
    assert "Pending approvals: 2" in text
    assert "Waiting over 24 hours: Old item" in text
    assert "New item" not in text
    statuses = {e.status for e in await env.entries()}
    assert statuses == {EntryStatus.PENDING_APPROVAL}


async def test_t237_pending_stranger_silent_and_in_recap(env: Env) -> None:
    await post_update(env.client, env.app, tu.text_message(STRANGER_ID, "hello", username="anon"))
    assert len([c for c in env.bot.sent_texts]) == 2
    with time_machine.travel(NOW + dt.timedelta(hours=30), tick=False):
        before = len(env.bot.calls)
        await post_update(env.client, env.app, tu.text_message(STRANGER_ID, "hello again?"))
        assert env.bot.calls[before:] == []
        await env.say("/recap", reply=False)
    recap = env.to_boss()[-1]
    assert recap.chat_id == BOSS_ID
    assert "Strangers waiting: anon" in (recap.text or "")
