"""Invoice pipeline entry points. See planning/build-plan.md (P2-T08) and
planning/decisions.md#D-033."""

from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Any

from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper import audit
from bookkeeper.agents import services
from bookkeeper.agents.graphs.invoice import build_graph, thread_id
from bookkeeper.db.models import (
    AuditActor,
    Document,
    EntryStatus,
    Invoice,
    JournalEntry,
)
from bookkeeper.telegram.router import HandlerContext


async def _graph(ctx: HandlerContext) -> Any:
    return build_graph(
        ctx, services.llm_for(ctx.settings), await services.checkpointer_for(ctx.settings)
    )


async def _invoice_for_run(ctx: HandlerContext, document: Document) -> Invoice:
    earlier = (
        await ctx.session.scalars(
            select(Invoice).where(Invoice.document_id == document.id).order_by(Invoice.id)
        )
    ).all()
    sender = ctx.sender
    if earlier:
        audit.record(
            ctx.session,
            AuditActor.AGENT,
            "document.resent",
            "document",
            document.id,
            {
                "sender_user_id": sender.user_id,
                "telegram_user_id": sender.telegram_user_id,
                "supplier_id": sender.supplier_id,
                "earlier_invoice_ids": [i.id for i in earlier],
            },
        )
        for invoice in earlier:
            has_entry = await ctx.session.scalar(
                select(JournalEntry.id).where(JournalEntry.invoice_id == invoice.id).limit(1)
            )
            if has_entry is None:
                return invoice
    invoice = Invoice(document_id=document.id, supplier_id=sender.supplier_id)
    ctx.session.add(invoice)
    await ctx.session.flush()
    return invoice


async def start(document_id: int, ctx: HandlerContext) -> None:
    document = await ctx.session.get(Document, document_id)
    if document is None:
        return
    invoice = await _invoice_for_run(ctx, document)
    await ctx.session.commit()
    graph = await _graph(ctx)
    config = {"configurable": {"thread_id": thread_id(invoice.id)}}
    await graph.ainvoke(
        {
            "document_id": document.id,
            "invoice_id": invoice.id,
            "entry_id": None,
            "kind": "normal",
            "outcome": "",
            "decision": None,
            "edit_text": None,
            "edited": False,
            "tell_supplier": False,
        },
        config,
    )


async def resume(ctx: HandlerContext, invoice_id: int, value: dict[str, Any]) -> None:
    graph = await _graph(ctx)
    config = {"configurable": {"thread_id": thread_id(invoice_id)}}
    await graph.ainvoke(Command(resume=value), config)


@dataclasses.dataclass(frozen=True, slots=True)
class PendingItem:
    entry_id: int
    invoice_id: int | None
    description: str
    age: dt.timedelta


async def pending_items(
    session: AsyncSession, *, older_than: dt.timedelta, now: dt.datetime | None = None
) -> list[PendingItem]:
    """See planning/01-prd.md#f-015 (F-015.7); the daily recap lists these."""
    instant = now or dt.datetime.now(dt.UTC)
    rows = await session.scalars(
        select(JournalEntry)
        .where(
            JournalEntry.status == EntryStatus.PENDING_APPROVAL,
            JournalEntry.created_at <= instant - older_than,
        )
        .order_by(JournalEntry.created_at)
    )
    return [PendingItem(e.id, e.invoice_id, e.description, instant - e.created_at) for e in rows]
