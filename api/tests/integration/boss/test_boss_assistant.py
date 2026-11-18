"""T-143, T-147, T-151, T-159, T-163, T-164, T-165 and Q&A answers (F-018)."""

import datetime as dt
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from bookkeeper.agents.boss import BossIntent
from bookkeeper.agents.llm import LLMResult
from bookkeeper.db.models import (
    Account,
    Bill,
    BillStatus,
    EntrySource,
    EntryStatus,
    JournalEntry,
    JournalLine,
    Payment,
    Period,
)
from bookkeeper.ledger import lock_period
from tests.integration.invoices.helpers import Env, revision
from tests.unit.checks.builders import make_invoice

D = Decimal


def intent(**fields: Any) -> LLMResult:
    return LLMResult(parsed=BossIntent(**fields), model="fake-flash")


async def _lines(env: Env, entry: JournalEntry) -> list[tuple[str, Decimal, Decimal]]:
    rows = await env.session.execute(
        select(Account.name, JournalLine.debit, JournalLine.credit)
        .join(Account, Account.id == JournalLine.account_id)
        .where(JournalLine.entry_id == entry.id)
        .order_by(JournalLine.line_no)
    )
    return [(n, d, c) for n, d, c in rows.all()]


async def test_t143_t147_sales_text_needs_confirm(env: Env) -> None:
    await env.say("sales today 1,850, cash 420, card 1,430", reply=False)
    text = env.card().text or ""
    assert "Sales 18 Nov 2026" in text
    assert "Dr Cash 420.00" in text
    assert "Dr Bank 1,430.00" in text
    assert "Cr Sales 1,697.25" in text
    assert "Cr Output GST 152.75" in text
    assert await env.entries(EntryStatus.POSTED) == []
    assert env.llm.calls == []

    await env.press(env.buttons()["Confirm"])
    [entry] = await env.entries(EntryStatus.POSTED)
    assert entry.date == dt.date(2026, 11, 18)
    assert entry.source == EntrySource.MANUAL
    assert "Posted JE-00001" in (env.to_boss()[-1].text or "")


async def test_sales_split_mismatch_asks_again(env: Env) -> None:
    await env.say("sales today 1,850, cash 420, card 1,400", reply=False)
    assert "is 1,820.00, not 1,850.00" in (env.to_boss()[-1].text or "")
    assert await env.entries() == []


async def test_t163_t164_manual_entry_confirm_posts(env: Env) -> None:
    env.llm.queue(
        "assistant",
        intent(
            intent="manual_entry",
            amount=D("50"),
            paid_from="cash",
            account="Packaging",
            description="Ice",
        ),
    )
    await env.say("paid 50 cash for ice today", reply=False)
    assert list(env.buttons()) == ["Confirm", "Edit", "Cancel"]
    text = env.card().text or ""
    assert "Dr Packaging 50.00" in text
    assert "Cr Cash 50.00" in text
    assert "18 Nov 2026" in text
    assert await env.entries(EntryStatus.POSTED) == []

    await env.press(env.buttons()["Confirm"])
    [entry] = await env.entries(EntryStatus.POSTED)
    assert entry.source == EntrySource.MANUAL
    assert await _lines(env, entry) == [
        ("Packaging", D("50.00"), D("0.00")),
        ("Cash", D("0.00"), D("50.00")),
    ]

    await env.press(env.buttons()["Confirm"])
    assert len(await env.entries(EntryStatus.POSTED)) == 1


async def test_t164_cancel_and_edit_post_nothing(env: Env) -> None:
    for button in ("Cancel", "Edit"):
        env.llm.queue(
            "assistant",
            intent(intent="manual_entry", amount=D("50"), paid_from="cash", account="Packaging"),
        )
        await env.say("paid 50 cash for ice today", reply=False)
        await env.press(env.buttons()[button])
    assert await env.entries(EntryStatus.POSTED) == []
    assert len(await env.entries(EntryStatus.REJECTED)) == 2


async def test_t165_locked_month_manual_entry_moves_to_open_period(env: Env) -> None:
    await lock_period(env.session, 2026, 10)
    env.llm.queue(
        "assistant",
        intent(
            intent="manual_entry",
            amount=D("50"),
            paid_from="cash",
            account="Packaging",
            date=dt.date(2026, 10, 20),
        ),
    )
    await env.say("paid 50 cash for ice on 20 Oct", reply=False)
    await env.press(env.buttons()["Confirm"])
    [entry] = await env.entries(EntryStatus.POSTED)
    assert entry.date == dt.date(2026, 11, 1)
    assert "20 Oct 2026" in (entry.note or "")


async def test_t159_question_changes_nothing(env: Env) -> None:
    await env.send(make_invoice())

    async def counts() -> tuple[int | None, ...]:
        return (
            await env.session.scalar(select(func.count()).select_from(JournalEntry)),
            await env.session.scalar(select(func.count()).select_from(JournalLine)),
            await env.session.scalar(select(func.count()).select_from(Bill)),
            await env.session.scalar(select(func.count()).select_from(Period)),
        )

    before = await counts()
    env.llm.queue("assistant", intent(intent="out_of_scope"))
    await env.say("delete JE-00001", reply=False)
    assert "can not help" in (env.to_boss()[-1].text or "")
    env.llm.queue("assistant", intent(intent="question", question="spend", subject="seafood"))
    await env.say("how much did I spend on seafood this month?", reply=False)
    assert env.to_boss()[-1].text == (
        "You spent 400.00 on COGS Seafood from 1 Nov 2026 to 18 Nov 2026."
    )
    assert await counts() == before
    [posted] = await env.entries(EntryStatus.POSTED)
    assert posted.entry_no == 1


async def test_questions_sales_supplier_and_balance(env: Env) -> None:
    await env.send(make_invoice())
    env.llm.queue("assistant", intent(intent="question", question="spend", subject="Ocean"))
    await env.say("what did I spend with ocean fresh?", reply=False)
    assert "You spent 400.00 on Ocean Fresh" in (env.to_boss()[-1].text or "")
    env.llm.queue("assistant", intent(intent="question", question="balance", subject="payable"))
    await env.say("how much do I owe?", reply=False)
    assert env.to_boss()[-1].text == "Accounts Payable is 436.00 as at 18 Nov 2026."
    env.llm.queue("assistant", intent(intent="question", question="sales", period="last_month"))
    await env.say("sales last month?", reply=False)
    assert env.to_boss()[-1].text == "Sales from 1 Oct 2026 to 31 Oct 2026 were 0.00."
    env.llm.queue("assistant", intent(intent="unclear", clarify="Which month do you mean?"))
    await env.say("how did we do?", reply=False)
    assert env.to_boss()[-1].text == "Which month do you mean?"


async def test_t151_bills_and_mark_paid(env: Env) -> None:
    await env.send(make_invoice())
    await env.say("/bills", reply=False)
    text = env.card().text or ""
    assert "Ocean Fresh INV-1043: 436.00, due 1 Dec 2026" in text
    [label] = list(env.buttons())
    assert label.startswith("Mark paid")

    await env.press(env.buttons()[label])
    proposal = env.card().text or ""
    assert "Dr Accounts Payable 436.00" in proposal
    assert "Cr Bank 436.00" in proposal
    assert list(env.buttons()) == ["Confirm", "Cancel"]
    await env.press(env.buttons()["Confirm"])

    [bill] = await env.bills()
    assert bill.status == BillStatus.PAID
    assert bill.paid_amount == D("436.00")
    [payment] = (await env.session.scalars(select(Payment))).all()
    assert payment.amount == D("436.00")
    assert len(await env.entries(EntryStatus.POSTED)) == 2

    await env.say("/bills", reply=False)
    assert env.to_boss()[-1].text == "No open bills."


async def test_edit_prompt_reply_still_goes_to_approvals(env: Env) -> None:
    await env.send(make_invoice(gst=D("40.00"), total=D("440.00")))
    await env.press(env.buttons()["Edit"])
    calls_before = len(env.llm.calls_for("assistant"))
    env.llm.queue("revise", revision(gst=D("36.00"), total=D("436.00")))
    await env.say("gst is 36", reply=True)
    assert len(env.llm.calls_for("assistant")) == calls_before
    assert env.llm.calls_for("revise")


async def test_two_mark_paid_proposals_pay_the_bill_once(env: Env) -> None:
    await env.send(make_invoice())
    await env.say("/bills", reply=False)
    [label] = list(env.buttons())
    pay = env.buttons()[label]
    await env.press(pay)
    first = env.buttons()["Confirm"]
    await env.press(pay)
    second = env.buttons()["Confirm"]
    assert first != second
    await env.press(first)
    await env.press(second)
    [bill] = await env.bills()
    assert bill.status == BillStatus.PAID
    assert bill.paid_amount == D("436.00")
    assert len((await env.session.scalars(select(Payment))).all()) == 1
    assert len(await env.entries(EntryStatus.POSTED)) == 2
    assert env.to_boss()[-1].text == "That one is already handled."
