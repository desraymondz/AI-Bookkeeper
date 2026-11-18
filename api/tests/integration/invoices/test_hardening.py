"""T-005 (pipeline paths), regression of T-132 and T-134. See planning/build-plan.md (P2-T10)."""

from decimal import Decimal

import pytest
from sqlalchemy import select

from bookkeeper import invoice_pipeline
from bookkeeper.agents import services
from bookkeeper.db.models import Approval, AuditLog, EntryStatus
from bookkeeper.ledger import LedgerError
from tests.integration.invoices.helpers import Env, revision
from tests.unit.checks.builders import make_invoice

BAD_GST = {"gst": Decimal("40.00"), "total": Decimal("440.00")}


async def _actions(env: Env, action: str) -> list[AuditLog]:
    rows = await env.session.scalars(select(AuditLog).where(AuditLog.action == action))
    return list(rows.all())


async def test_ledger_refusal_notifies_boss_and_audits(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    await env.send(make_invoice(**BAD_GST))

    async def refuse(*args: object, **kwargs: object) -> None:
        raise LedgerError("The period is locked.")

    monkeypatch.setattr("bookkeeper.agents.graphs.invoice.post_held", refuse)
    await env.press(env.buttons()["Approve"])

    assert "I could not post" in (env.to_boss()[-1].text or "")
    assert "The period is locked." in (env.to_boss()[-1].text or "")
    assert len(await _actions(env, "posting.refused")) == 1
    assert await env.entries(EntryStatus.POSTED) == []


async def test_failed_resume_leaves_decision_open_and_press_again_works(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    await env.send(make_invoice(**BAD_GST))
    approve = env.buttons()["Approve"]
    real = invoice_pipeline.resume
    calls = 0

    async def flaky(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")
        await real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(invoice_pipeline, "resume", flaky)
    await env.press(approve)

    approval = await env.session.scalar(select(Approval))
    assert approval is not None
    await env.session.refresh(approval)
    assert approval.decision is None
    assert approval.decided_at is None
    assert await env.entries(EntryStatus.POSTED) == []
    assert env.bot.calls_for("edit_message_text") == []

    await env.press(approve)
    [entry] = await env.entries(EntryStatus.POSTED)
    assert entry.id is not None
    assert len(await env.bills()) == 1


async def test_failed_edit_resume_keeps_edit_awaited(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    await env.send(make_invoice(**BAD_GST))
    await env.press(env.buttons()["Edit"])
    real = invoice_pipeline.resume
    calls = 0

    async def flaky(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")
        await real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(invoice_pipeline, "resume", flaky)
    env.llm.queue("revise", revision(total=Decimal("436.00")))
    await env.say("total is 436.00")
    await env.say("total is 436.00")
    assert "Cr Accounts Payable 436.00" in (env.card().text or "")


async def test_text_not_replying_to_edit_prompt_is_not_claimed(env: Env) -> None:
    await env.send(make_invoice(**BAD_GST))
    await env.press(env.buttons()["Edit"])
    before = len(env.to_boss())
    await env.say("hello there", reply=False)
    assert len(env.to_boss()) == before
    approval = await env.session.scalar(select(Approval))
    assert approval is not None
    await env.session.refresh(approval)
    assert approval.note == "awaiting_edit"


async def test_services_close_releases_pool_and_lifespan_calls_it(
    env: Env, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with services.override():
        settings = env.app.state.settings.model_copy(update={"database_url": database_url})
        saver = await services.checkpointer_for(settings)
        pool = saver.conn  # type: ignore[attr-defined]
        assert not pool.closed
        await services.close()
        assert pool.closed
        assert services._checkpointer is None

    closed: list[bool] = []

    async def record() -> None:
        closed.append(True)

    monkeypatch.setattr(services, "close", record)
    async with env.app.router.lifespan_context(env.app):
        pass
    assert closed == [True]
