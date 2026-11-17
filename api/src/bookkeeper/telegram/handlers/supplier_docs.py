"""Supplier document intake. See planning/01-prd.md#f-011."""

from __future__ import annotations

import datetime as dt

from telegram import Update

from bookkeeper import invoice_pipeline, storage
from bookkeeper.db.models import Supplier, User
from bookkeeper.telegram import handlers
from bookkeeper.telegram.router import Handler, HandlerContext, Role
from bookkeeper.templates import render


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def matches(update: Update) -> bool:
    message = update.message
    return message is not None and (message.document is not None or bool(message.photo))


def _file_ref(update: Update) -> tuple[str, int | None]:
    message = update.message
    assert message is not None
    if message.document is not None:
        return message.document.file_id, message.document.file_size
    largest = message.photo[-1]
    return largest.file_id, largest.file_size


async def handle(ctx: HandlerContext) -> None:
    file_id, declared_size = _file_ref(ctx.update)
    if declared_size is not None and declared_size > storage.MAX_BYTES:
        await ctx.reply(render("document_too_big"))
        return

    data = await ctx.download(file_id)
    if len(data) > storage.MAX_BYTES:
        await ctx.reply(render("document_too_big"))
        return
    mime = storage.detect_type(data)
    if mime is None:
        await ctx.reply(render("document_wrong_type"))
        return

    supplier = await ctx.session.get(Supplier, ctx.sender.supplier_id)
    user = await ctx.session.get(User, ctx.sender.user_id)
    if supplier is None or user is None:
        return

    stored = await storage.store_document(
        ctx.session,
        ctx.settings.storage_dir,
        data=data,
        mime=mime,
        supplier_name=supplier.name,
        sender_user_id=user.id,
        received_at=now(),
    )
    await ctx.reply(render("document_received"))
    await ctx.session.commit()
    await invoice_pipeline.start(stored.document.id)


HANDLER = Handler("supplier_docs", frozenset({Role.SUPPLIER}), matches, handle)
handlers.HANDLERS.append(HANDLER)
