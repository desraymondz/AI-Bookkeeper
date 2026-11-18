"""T-019, T-130 to T-139, T-141, T-142."""

from decimal import Decimal

from sqlalchemy import select

from bookkeeper.db.models import (
    Approval,
    AuditActor,
    AuditLog,
    EntryKind,
    EntrySource,
    EntryStatus,
)
from tests.integration.invoices.helpers import Env, revision
from tests.integration.telegram.conftest import BOSS_ID, SUPPLIER_ID
from tests.unit.checks.builders import make_invoice

D = Decimal
BAD_GST = {"gst": D("40.00"), "total": D("440.00")}


async def _audit(env: Env, action: str) -> list[AuditLog]:
    rows = await env.session.scalars(select(AuditLog).where(AuditLog.action == action))
    return list(rows.all())


async def test_t130_card_explains_gst_in_plain_words(env: Env) -> None:
    await env.send(make_invoice(**BAD_GST))
    text = env.card().text or ""
    assert "GST is 40.00 but 9% of 400.00 is 36.00" in text
    assert "Dr COGS Seafood 400.00" in text
    assert "Cr Accounts Payable 440.00" in text
    assert list(env.buttons()) == ["Approve", "Edit", "Reject"]


async def test_t131_card_lists_every_failed_check(env: Env) -> None:
    await env.send(make_invoice())
    cheaper = make_invoice(
        invoice_no="INV-2000",
        subtotal=D("420.00"),
        gst=D("40.00"),
        total=D("460.00"),
        lines=[
            *make_invoice().lines[:1],
            make_invoice()
            .lines[1]
            .model_copy(
                update={"unit_price": D("35.00"), "qty": D("4"), "line_total": D("140.00")}
            ),
        ],
    )
    await env.send(cheaper)
    text = env.card().text or ""
    assert "GST:" in text
    assert "Price change:" in text


async def test_t132_t133_approve_posts_once_with_bill(env: Env) -> None:
    await env.send(make_invoice(**BAD_GST))
    approve = env.buttons()["Approve"]
    await env.press(approve)
    await env.press(approve)
    [entry] = await env.entries(EntryStatus.POSTED)
    assert entry.source == EntrySource.BOSS_APPROVED
    assert [str(line) for line in [(await env.bills())[0].amount]] == ["440.00"]
    assert len(await env.bills()) == 1
    assert len(await env.entries()) == 1
    assert len(await _audit(env, "approval.approve")) == 1
    [row] = await _audit(env, "approval.approve")
    assert row.actor == AuditActor.BOSS
    approval = await env.session.scalar(select(Approval))
    assert approval is not None
    assert approval.decided_at is not None
    assert env.bot.calls_for("edit_message_text")[0].reply_markup is None


async def test_t134_edit_total_reruns_checks_and_sends_new_card(env: Env) -> None:
    await env.send(make_invoice(total=D("446.00")))
    assert "Arithmetic:" in (env.card().text or "")
    await env.press(env.buttons()["Edit"])
    assert "Tell me what to change" in (env.to_boss()[-1].text or "")
    env.llm.queue("revise", revision(total=D("436.00")))
    await env.say("total is 436.00")
    card = env.card().text or ""
    assert "Arithmetic" not in card
    assert "Cr Accounts Payable 436.00" in card
    assert await env.entries(EntryStatus.POSTED) == []
    assert len(await env.entries()) == 1
    assert (await _audit(env, "approval.edit"))[0].actor == AuditActor.BOSS
    await env.press(env.buttons()["Approve"])
    [entry] = await env.entries(EntryStatus.POSTED)
    assert entry.source == EntrySource.BOSS_APPROVED
    assert (await env.bills())[0].amount == D("436.00")


async def test_t135_edit_account_changes_debit_line(env: Env) -> None:
    await env.send(make_invoice(**BAD_GST))
    await env.press(env.buttons()["Edit"])
    env.llm.queue("revise", revision(expense_account="Packaging"))
    await env.say("use Packaging account")
    card = env.card().text or ""
    assert "Dr Packaging 400.00" in card
    assert "COGS Seafood" not in card


async def test_edit_with_unknown_account_says_so_and_keeps_card(env: Env) -> None:
    await env.send(make_invoice(**BAD_GST))
    await env.press(env.buttons()["Edit"])
    env.llm.queue("revise", revision(expense_account="Yachts"))
    await env.say("use Yachts account")
    assert any("no expense account called Yachts" in (c.text or "") for c in env.to_boss())
    assert "Dr COGS Seafood" in (env.card().text or "")
    assert await env.entries(EntryStatus.POSTED) == []


async def test_t136_reject_and_tell_supplier(env: Env) -> None:
    await env.send(make_invoice(**BAD_GST))
    acks = len(env.to_supplier())
    await env.press(env.buttons()["Reject"])
    [entry] = await env.entries()
    assert entry.status == EntryStatus.REJECTED
    assert "Tell the supplier?" in (env.to_boss()[-1].text or "")
    await env.press(env.buttons()["Yes"])
    notes = env.to_supplier()[acks:]
    assert len(notes) == 1
    text = notes[0].text or ""
    assert "INV-1043" not in text
    assert "440" not in text
    assert await env.entries(EntryStatus.POSTED) == []
    assert await env.bills() == []
    assert (await _audit(env, "supplier.notified"))[0].actor == AuditActor.AGENT
    assert (await _audit(env, "approval.reject"))[0].actor == AuditActor.BOSS


async def test_t137_reject_without_telling_supplier(env: Env) -> None:
    await env.send(make_invoice(**BAD_GST))
    acks = len(env.to_supplier())
    await env.press(env.buttons()["Reject"])
    await env.press(env.buttons()["No"])
    assert len(env.to_supplier()) == acks
    assert await env.entries(EntryStatus.POSTED) == []


async def test_t138_duplicate_card_names_earlier_entry(env: Env) -> None:
    payload = await env.send(make_invoice())
    assert [e.entry_no for e in await env.entries(EntryStatus.POSTED)] == [1]
    await env.send(make_invoice(), data=payload)
    text = env.card().text or ""
    assert "JE-00001" in text
    assert list(env.buttons()) == ["Ignore duplicate", "Post anyway"]
    resent = await _audit(env, "document.resent")
    assert resent[0].detail_json["telegram_user_id"] == SUPPLIER_ID

    await env.press(env.buttons()["Ignore duplicate"])
    assert len(await env.entries(EntryStatus.POSTED)) == 1
    assert len(await env.entries(EntryStatus.REJECTED)) == 1

    await env.send(make_invoice(), data=payload)
    await env.press(env.buttons()["Post anyway"])
    assert len(await env.entries(EntryStatus.POSTED)) == 2


async def test_resend_after_unreadable_reruns_same_invoice(env: Env) -> None:
    from bookkeeper.agents.llm import LLMResult

    env.llm.queue("extract", *[LLMResult(text="nope", model="m")] * 3)
    payload = b"%PDF-1.4 same bytes"
    await env.send_file(payload)
    assert await env.entries() == []
    await env.send(make_invoice(), data=payload)
    [entry] = await env.entries(EntryStatus.POSTED)
    assert entry.source == EntrySource.AUTO
    assert len(await _audit(env, "document.resent")) == 1


async def test_t139_revision_reverses_original_and_updates_bill(env: Env) -> None:
    await env.send(make_invoice())
    revised = make_invoice(
        subtotal=D("432.00"),
        gst=D("38.88"),
        total=D("470.88"),
        lines=[
            make_invoice().lines[0],
            make_invoice()
            .lines[1]
            .model_copy(update={"unit_price": D("38.00"), "line_total": D("152.00")}),
        ],
    )
    await env.send(revised)
    text = env.card().text or ""
    assert "Revised invoice" in text
    assert "Old total 436.00 (JE-00001)" in text
    assert "new total 470.88" in text
    await env.press(env.buttons()["Approve"])
    posted = await env.entries(EntryStatus.POSTED)
    assert sorted(e.kind for e in posted) == [
        EntryKind.NORMAL,
        EntryKind.NORMAL,
        EntryKind.REVERSAL,
    ]
    original = posted[0]
    [reversal] = [e for e in posted if e.kind == EntryKind.REVERSAL]
    new = posted[1]
    assert reversal.reverses_id == original.id
    assert new.reverses_id == original.id
    [bill] = await env.bills()
    assert bill.amount == D("470.88")


async def test_t141_supplier_and_stranger_presses_do_nothing(env: Env) -> None:
    await env.send(make_invoice(**BAD_GST))
    buttons = dict(env.buttons())
    before = len(env.bot.calls)
    for user_id in (SUPPLIER_ID, 99999):
        for data in buttons.values():
            await env.press(data, user_id=user_id)
    assert len(env.bot.calls) == before
    assert len(await env.entries(EntryStatus.PENDING_APPROVAL)) == 1
    assert await env.entries(EntryStatus.POSTED) == []
    await env.say("total is 1", user_id=SUPPLIER_ID)
    assert len(await env.entries(EntryStatus.PENDING_APPROVAL)) == 1


async def test_t142_other_buttons_ignored_for_non_boss(env: Env) -> None:
    await env.send(make_invoice(**BAD_GST))
    before = len(env.bot.calls)
    for data in ("st_add:1", "st_blk:1", "close_ok:1", "sales_ok:1", "pay_ok:1"):
        for user_id in (SUPPLIER_ID, 99999):
            await env.press(data, user_id=user_id)
    assert len(env.bot.calls) == before
    assert BOSS_ID
