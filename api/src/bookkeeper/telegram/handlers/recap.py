"""/recap command. See planning/01-prd.md#f-020-daily-recap and planning/decisions.md#D-036."""

from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update

from bookkeeper import invoice_pipeline
from bookkeeper.ledger import business_today, format_money
from bookkeeper.ledger.periods import format_day
from bookkeeper.reports.assistant import OpenBill
from bookkeeper.reports.recap import daily_figures
from bookkeeper.settings_service import get_settings
from bookkeeper.telegram import handlers as registry
from bookkeeper.telegram.handlers.stranger import pending_strangers
from bookkeeper.telegram.router import Handler, HandlerContext, Role
from bookkeeper.templates import render

RECAP_COMMAND = "/recap"
PENDING_AGE = dt.timedelta(hours=24)


def matches(update: Update) -> bool:
    message = update.message
    text = message.text if message is not None else None
    return bool(text) and (text or "").split("@")[0].strip().lower() == RECAP_COMMAND


def _bill(bill: OpenBill) -> str:
    ref = f" {bill.invoice_no}" if bill.invoice_no else ""
    return f"{bill.supplier}{ref} {format_money(bill.remaining)}, due {format_day(bill.due_date)}"


async def build_recap(session: AsyncSession, now: dt.datetime | None = None) -> str:
    settings = await get_settings(session)
    within = settings.reminder_days if settings is not None else 3
    day = await business_today(session, now)
    figures = await daily_figures(session, day, within)
    old = await invoice_pipeline.pending_items(session, older_than=PENDING_AGE, now=now)
    strangers = await pending_strangers(session)
    quiet = (
        figures.invoice_count == 0
        and figures.sales_total == 0
        and figures.pending_count == 0
        and not figures.due_soon
        and not figures.overdue
        and not strangers
    )
    return render(
        "recap",
        quiet=quiet,
        day=format_day(day),
        invoice_count=figures.invoice_count,
        invoice_total=format_money(figures.invoice_total),
        sales_total=format_money(figures.sales_total),
        pending_count=figures.pending_count,
        old_pending=[item.description for item in old],
        within=within,
        due_soon=[_bill(b) for b in figures.due_soon],
        overdue=[_bill(b) for b in figures.overdue],
        strangers=[s.display_name or s.username or str(s.telegram_user_id) for s in strangers],
    )


async def handle(ctx: HandlerContext) -> None:
    await ctx.reply(await build_recap(ctx.session))


registry.HANDLERS.append(Handler("recap", frozenset({Role.BOSS}), matches, handle))
