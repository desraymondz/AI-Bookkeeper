"""Supplier chat text gets a fixed reply. See planning/01-prd.md (F-008.3)."""

from telegram import Update

from bookkeeper.telegram import handlers
from bookkeeper.telegram.router import Handler, HandlerContext, Role
from bookkeeper.templates import render


def matches(update: Update) -> bool:
    return update.message is not None and bool(update.message.text)


async def handle(ctx: HandlerContext) -> None:
    await ctx.reply(render("supplier_text_reply"))


HANDLER = Handler("supplier_text", frozenset({Role.SUPPLIER}), matches, handle)
handlers.HANDLERS.append(HANDLER)
