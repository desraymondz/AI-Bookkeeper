"""Approve, Edit, Reject and related buttons. See planning/01-prd.md#f-015 and
planning/03-tech-stack.md#5-langgraph-layout."""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import select
from telegram import Update

from bookkeeper import audit, invoice_pipeline
from bookkeeper.agents.graphs.invoice import (
    APPROVE,
    EDIT,
    IGNORE_DUPLICATE,
    POST_ANYWAY,
    REJECT,
)
from bookkeeper.db.models import (
    Approval,
    ApprovalDecision,
    AuditActor,
    EntryStatus,
    JournalEntry,
)
from bookkeeper.telegram import handlers as registry
from bookkeeper.telegram.keyboards import decode_callback
from bookkeeper.telegram.router import Handler, HandlerContext, Role
from bookkeeper.templates import render

AWAITING_EDIT = "awaiting_edit"
EDIT_RECEIVED = "edit_received"
TOLD, NOT_TOLD = "supplier_told", "supplier_not_told"

DECISIONS = {
    "ap_ok": (APPROVE, ApprovalDecision.APPROVE, "Approved."),
    "ap_ed": (EDIT, ApprovalDecision.EDIT, "Edit requested."),
    "ap_rj": (REJECT, ApprovalDecision.REJECT, "Rejected."),
    "ap_ig": (IGNORE_DUPLICATE, ApprovalDecision.IGNORE_DUPLICATE, "Duplicate ignored."),
    "ap_pa": (POST_ANYWAY, ApprovalDecision.POST_ANYWAY, "Posting anyway."),
}
TELL_ACTIONS = {"ap_ty": True, "ap_tn": False}
ALL_ACTIONS = frozenset(DECISIONS) | frozenset(TELL_ACTIONS)


def matches_callback(update: Update) -> bool:
    query = update.callback_query
    return (
        query is not None
        and query.data is not None
        and (decode_callback(query.data)[0] in ALL_ACTIONS)
    )


def matches_text(update: Update) -> bool:
    message = update.message
    if message is None or not message.text or message.text.startswith("/"):
        return False
    replied = message.reply_to_message
    return replied is not None and replied.text == render("invoice_edit_prompt")


async def _latest_approval(ctx: HandlerContext, entry_id: int) -> Approval | None:
    return await ctx.session.scalar(
        select(Approval).where(Approval.entry_id == entry_id).order_by(Approval.id.desc()).limit(1)
    )


async def _strip_buttons(ctx: HandlerContext, label: str) -> None:
    query = ctx.update.callback_query
    message = query.message if query else None
    message_id = getattr(message, "message_id", None)
    text = getattr(message, "text", None)
    if message_id is not None and text:
        await ctx.edit(message_id, f"{text}\n\n{label}", reply_markup=None)


async def _resume_or_undo(
    ctx: HandlerContext,
    invoice_id: int,
    entry_id: int,
    approval_id: int,
    value: dict[str, Any],
    *,
    entry_status: EntryStatus,
    note: str | None,
    decided: bool,
) -> None:
    """Decision and resume act as one unit. See planning/build-plan.md (P2-T10)."""
    try:
        await invoice_pipeline.resume(ctx, invoice_id, value)
    except Exception:
        await ctx.session.rollback()
        entry = await ctx.session.get(JournalEntry, entry_id, populate_existing=True)
        approval = await ctx.session.get(Approval, approval_id, populate_existing=True)
        if entry is not None and approval is not None and entry.status == entry_status:
            approval.note = note
            if decided:
                approval.decision = None
                approval.decided_at = None
            audit.record(
                ctx.session,
                AuditActor.SYSTEM,
                "approval.resume_failed",
                "journal_entry",
                entry_id,
                {"value": sorted(value)},
            )
            await ctx.session.commit()
        raise
    await ctx.session.commit()


async def handle_callback(ctx: HandlerContext) -> None:
    query = ctx.update.callback_query
    if query is None or query.data is None:
        return
    action, args = decode_callback(query.data)
    if not args or not args[0].isdigit():
        return
    entry_id = int(args[0])
    entry = await ctx.session.get(
        JournalEntry, entry_id, with_for_update=True, populate_existing=True
    )
    if entry is None or entry.invoice_id is None:
        await ctx.answer_callback(query.id)
        return
    approval = await _latest_approval(ctx, entry_id)
    handled = render("invoice_already_handled")

    if action in TELL_ACTIONS:
        if (
            entry.status != EntryStatus.REJECTED
            or approval is None
            or approval.note in (TOLD, NOT_TOLD)
        ):
            await ctx.answer_callback(query.id, handled)
            return
        tell = TELL_ACTIONS[action]
        approval.note = TOLD if tell else NOT_TOLD
        audit.record(
            ctx.session,
            AuditActor.BOSS,
            "approval.tell_supplier" if tell else "approval.dont_tell_supplier",
            "journal_entry",
            entry_id,
        )
        await ctx.answer_callback(query.id)
        await _resume_or_undo(
            ctx,
            entry.invoice_id,
            entry_id,
            approval.id,
            {"tell": tell},
            entry_status=EntryStatus.REJECTED,
            note=None,
            decided=False,
        )
        await _strip_buttons(ctx, "Yes." if tell else "No.")
        return

    decision, enum_value, label = DECISIONS[action]
    if entry.status != EntryStatus.PENDING_APPROVAL or approval is None:
        await ctx.answer_callback(query.id, handled)
        return
    if approval.note == AWAITING_EDIT or approval.decision is not None:
        await ctx.answer_callback(query.id, handled)
        return
    approval.decision = enum_value
    approval.decided_at = dt.datetime.now(dt.UTC)
    if decision == EDIT:
        approval.note = AWAITING_EDIT
    audit.record(
        ctx.session,
        AuditActor.BOSS,
        f"approval.{decision}",
        "journal_entry",
        entry_id,
        {"message_id": approval.telegram_message_id},
    )
    await ctx.answer_callback(query.id)
    await _resume_or_undo(
        ctx,
        entry.invoice_id,
        entry_id,
        approval.id,
        {"decision": decision},
        entry_status=EntryStatus.PENDING_APPROVAL,
        note=None,
        decided=True,
    )
    await _strip_buttons(ctx, label)


async def awaiting_edit(ctx: HandlerContext) -> tuple[Approval, JournalEntry] | None:
    """Callers that read boss free text check this first. See planning/01-prd.md#f-015 (F-015.3)."""
    row = (
        await ctx.session.execute(
            select(Approval, JournalEntry)
            .join(JournalEntry, JournalEntry.id == Approval.entry_id)
            .where(
                Approval.note == AWAITING_EDIT,
                JournalEntry.status == EntryStatus.PENDING_APPROVAL,
            )
            .order_by(Approval.id.desc())
            .limit(1)
        )
    ).first()
    return None if row is None else (row[0], row[1])


async def handle_text(ctx: HandlerContext) -> None:
    message = ctx.update.message
    pending = await awaiting_edit(ctx)
    if message is None or message.text is None or pending is None:
        return
    approval, entry = pending
    if entry.invoice_id is None:
        return
    approval.note = EDIT_RECEIVED
    audit.record(
        ctx.session,
        AuditActor.BOSS,
        "approval.edit_text",
        "journal_entry",
        entry.id,
        {"text": message.text[:500]},
    )
    await _resume_or_undo(
        ctx,
        entry.invoice_id,
        entry.id,
        approval.id,
        {"text": message.text},
        entry_status=EntryStatus.PENDING_APPROVAL,
        note=AWAITING_EDIT,
        decided=False,
    )


registry.HANDLERS.append(
    Handler("approvals_callback", frozenset({Role.BOSS}), matches_callback, handle_callback)
)
registry.HANDLERS.append(
    Handler("approvals_text", frozenset({Role.BOSS}), matches_text, handle_text)
)
