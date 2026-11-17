"""Deep link binding. See planning/01-prd.md (F-006.2, F-006.3, F-007.3)."""

from telegram import Update

from bookkeeper import linking
from bookkeeper.telegram import handlers
from bookkeeper.telegram.router import Handler, HandlerContext, Role
from bookkeeper.templates import render

START_COMMAND = "/start"


def _payload(update: Update) -> str | None:
    text = update.message.text if update.message is not None else None
    if not text:
        return None
    command, _, rest = text.partition(" ")
    if command.split("@")[0] != START_COMMAND or not rest.strip():
        return None
    return rest.strip()


def matches(update: Update) -> bool:
    return _payload(update) is not None


async def handle(ctx: HandlerContext) -> None:
    token = _payload(ctx.update)
    user = ctx.update.effective_user
    if token is None or user is None:
        return
    result = await linking.redeem(
        ctx.session,
        token,
        telegram_user_id=user.id,
        username=user.username,
        display_name=user.full_name,
    )
    match result.outcome:
        case linking.Outcome.BOSS_LINKED:
            await ctx.reply(render("link_boss_ok"))
        case linking.Outcome.SUPPLIER_LINKED:
            supplier = result.supplier_name or ""
            await ctx.reply(render("link_supplier_ok", person=user.full_name, supplier=supplier))
            await ctx.to_boss(
                render("link_supplier_boss_fyi", person=user.full_name, supplier=supplier)
            )
        case linking.Outcome.INVALID:
            await ctx.reply(render("link_invalid"))


HANDLER = Handler("start", frozenset(Role), matches, handle)
handlers.HANDLERS.insert(0, HANDLER)
