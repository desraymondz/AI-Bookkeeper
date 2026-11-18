"""Boss assistant: questions, manual entries, sales and bill payments.
See planning/01-prd.md (F-016, F-017.2, F-018, F-019) and planning/decisions.md#D-036."""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from telegram import Update

from bookkeeper.agents import services
from bookkeeper.agents.boss import (
    BossIntent,
    ProposedLine,
    classify,
    parse_sales,
    payment_lines,
    sales_lines,
    split_mismatch,
)
from bookkeeper.agents.tool_gate import ToolCall, ToolFn, run_tool_call
from bookkeeper.db.models import (
    Account,
    AccountType,
    AuditActor,
    Bill,
    BillStatus,
    EntrySource,
    EntryStatus,
    Invoice,
    JournalEntry,
    Payment,
    Supplier,
)
from bookkeeper.ledger import (
    EntryDraft,
    LedgerError,
    LineDraft,
    business_today,
    format_entry_no,
    format_money,
    hold_entry,
    post_held,
    reject_held,
)
from bookkeeper.ledger.periods import format_day
from bookkeeper.reports import assistant as tools
from bookkeeper.reports.dates import Preset, resolve_range_for_business
from bookkeeper.settings_service import get_settings
from bookkeeper.telegram import handlers as registry
from bookkeeper.telegram.keyboards import Button, decode_callback, inline_keyboard
from bookkeeper.telegram.router import Handler, HandlerContext, Role
from bookkeeper.templates import render

log = logging.getLogger(__name__)

CONFIRM, EDIT, CANCEL, PAY_CONFIRM, PAY = "bx_ok", "bx_ed", "bx_no", "bp_ok", "bl_pay"
CALLBACKS = frozenset({CONFIRM, EDIT, CANCEL, PAY_CONFIRM, PAY})
BILLS_COMMAND = "/bills"
MAX_BILL_BUTTONS = 10
MAX_CLARIFY = 200


def _text(update: Update) -> str | None:
    message = update.message
    return message.text if message is not None and message.text else None


def matches_text(update: Update) -> bool:
    text = _text(update)
    return text is not None and not text.startswith("/")


def matches_bills(update: Update) -> bool:
    text = _text(update)
    return text is not None and text.split("@")[0].strip().lower() == BILLS_COMMAND


def matches_callback(update: Update) -> bool:
    query = update.callback_query
    return (
        query is not None and query.data is not None and decode_callback(query.data)[0] in CALLBACKS
    )


async def _accounts_by_name(ctx: HandlerContext, names: Sequence[str]) -> dict[str, Account]:
    rows = await ctx.session.scalars(
        select(Account).where(Account.name.in_(list(names)), Account.active.is_(True))
    )
    return {a.name: a for a in rows}


async def _expense_accounts(ctx: HandlerContext) -> list[Account]:
    rows = await ctx.session.scalars(
        select(Account)
        .where(Account.type == AccountType.EXPENSE, Account.active.is_(True))
        .order_by(Account.code)
    )
    return list(rows)


def _clarify(intent: BossIntent) -> str | None:
    return (intent.clarify or "")[:MAX_CLARIFY] or None


def _line_text(line: ProposedLine) -> str:
    if line.debit:
        return f"Dr {line.account} {format_money(line.debit)}"
    return f"Cr {line.account} {format_money(line.credit)}"


async def _propose(
    ctx: HandlerContext,
    title: str,
    day: dt.date,
    lines: list[ProposedLine],
    *,
    bill_id: int | None = None,
) -> None:
    accounts = await _accounts_by_name(ctx, [ln.account for ln in lines])
    draft = EntryDraft(
        date=day,
        description=title,
        lines=[LineDraft(accounts[ln.account].id, ln.debit, ln.credit) for ln in lines],
        source=EntrySource.MANUAL,
    )
    entry = await hold_entry(ctx.session, draft, status=EntryStatus.PROPOSED, actor=AuditActor.BOSS)
    if bill_id is None:
        buttons = [
            Button("Confirm", CONFIRM, (entry.id,)),
            Button("Edit", EDIT, (entry.id,)),
            Button("Cancel", CANCEL, (entry.id,)),
        ]
    else:
        buttons = [
            Button("Confirm", PAY_CONFIRM, (entry.id, bill_id)),
            Button("Cancel", CANCEL, (entry.id,)),
        ]
    text = render(
        "boss_proposal",
        title=title,
        date=format_day(day),
        lines=[_line_text(line) for line in lines],
    )
    await ctx.reply(text, reply_markup=inline_keyboard([buttons]))


async def _range(ctx: HandlerContext, period: str | None) -> tuple[dt.date, dt.date]:
    if period == "today":
        today = await business_today(ctx.session)
        return today, today
    preset = Preset(period) if period else Preset.THIS_MONTH
    rng = await resolve_range_for_business(ctx.session, preset)
    return rng.start, rng.end


async def _bill_label(bill: tools.OpenBill) -> str:
    ref = f" {bill.invoice_no}" if bill.invoice_no else ""
    return f"{bill.supplier}{ref}: {format_money(bill.remaining)}, due {format_day(bill.due_date)}"


async def _send_bills(ctx: HandlerContext) -> None:
    outcome = await run_tool_call(
        ctx.session, ctx.sender, ToolCall("open_bills"), {"open_bills": _open_bills(ctx)}
    )
    bills: list[tools.OpenBill] = outcome.value if outcome.ran else []
    labels = [await _bill_label(b) for b in bills]
    rows = [
        [Button(f"Mark paid: {b.supplier} {b.invoice_no or b.bill_id}"[:60], PAY, (b.bill_id,))]
        for b in bills[:MAX_BILL_BUTTONS]
    ]
    await ctx.reply(
        render("boss_bills", bills=labels), reply_markup=inline_keyboard(rows) if rows else None
    )


def _open_bills(ctx: HandlerContext) -> Any:
    async def run() -> list[tools.OpenBill]:
        return await tools.open_bills(ctx.session)

    return run


async def _answer(ctx: HandlerContext, intent: BossIntent) -> None:
    if intent.question == "bills":
        await _send_bills(ctx)
        return
    start, end = await _range(ctx, intent.period)
    session = ctx.session

    async def spend(subject: str | None) -> tools.Amount | None:
        return await tools.spend(session, subject, start, end)

    async def sales() -> tools.Amount:
        return await tools.sales(session, start, end)

    async def balance(subject: str) -> tools.Amount | None:
        return await tools.account_balance(session, subject, end)

    registry_tools: dict[str, ToolFn] = {"spend": spend, "sales": sales, "balance": balance}
    if intent.question == "spend":
        call = ToolCall("spend", {"subject": intent.subject})
    elif intent.question == "sales":
        call = ToolCall("sales")
    elif intent.question == "balance" and intent.subject:
        call = ToolCall("balance", {"subject": intent.subject})
    else:
        await ctx.reply(render("boss_unclear", question=_clarify(intent)))
        return
    outcome = await run_tool_call(ctx.session, ctx.sender, call, registry_tools)
    result: tools.Amount | None = outcome.value if outcome.ran else None
    if result is None:
        await ctx.reply(render("boss_not_found", subject=intent.subject or "that"))
        return
    values = {
        "label": result.label,
        "amount": format_money(result.amount),
        "start": format_day(start),
        "end": format_day(end),
        "date": format_day(end),
    }
    template = {"spend": "boss_spend", "sales": "boss_sales", "balance": "boss_balance"}
    await ctx.reply(render(template[call.name], **values))


async def _sales(
    ctx: HandlerContext, total: Decimal, cash: Decimal | None, card: Decimal | None, day: dt.date
) -> None:
    settings = await get_settings(ctx.session)
    registered = settings.gst_registered if settings is not None else False
    rate = settings.gst_rate if settings is not None else Decimal(0)
    lines = sales_lines(total, cash, card, gst_registered=registered, gst_rate=rate)
    await _propose(ctx, f"Sales {format_day(day)}", day, lines)


async def _manual(ctx: HandlerContext, intent: BossIntent, today: dt.date) -> None:
    expense = await _expense_accounts(ctx)
    match = None
    if intent.account:
        wanted = intent.account.strip().lower()
        match = next((a for a in expense if a.name.lower() == wanted), None) or next(
            (a for a in expense if wanted in a.name.lower()), None
        )
    if intent.amount is None or intent.amount <= 0:
        await ctx.reply(render("boss_unclear", question=_clarify(intent)))
        return
    if match is None:
        names = ", ".join(a.name for a in expense)
        await ctx.reply(render("boss_account_unknown", accounts=names))
        return
    day = intent.date or today
    title = (intent.description or f"Paid {match.name}").strip()[:120]
    lines = payment_lines(intent.paid_from or "cash", match.name, intent.amount)
    await _propose(ctx, title, day, lines)


async def handle_text(ctx: HandlerContext) -> None:
    text = _text(ctx.update)
    if text is None:
        return
    today = await business_today(ctx.session)
    figures = parse_sales(text)
    if figures is not None:
        if split_mismatch(figures):
            await ctx.reply(
                render(
                    "boss_sales_mismatch",
                    cash=format_money(figures.cash or Decimal(0)),
                    card=format_money(figures.card or Decimal(0)),
                    sum=format_money((figures.cash or Decimal(0)) + (figures.card or Decimal(0))),
                    total=format_money(figures.total),
                )
            )
            return
        day = today - dt.timedelta(days=1) if figures.yesterday else today
        await _sales(ctx, figures.total, figures.cash, figures.card, day)
        return
    expense = [a.name for a in await _expense_accounts(ctx)]
    try:
        intent = await classify(
            services.llm_for(ctx.settings), text, today=today, expense_accounts=expense
        )
    except Exception:
        log.exception("boss intent failed")
        await ctx.reply(render("boss_unclear", question=None))
        return
    match intent.intent:
        case "question":
            await _answer(ctx, intent)
        case "manual_entry":
            await _manual(ctx, intent, today)
        case "sales" if intent.amount is not None:
            await _sales(ctx, intent.amount, intent.cash, intent.card, intent.date or today)
        case "unclear" | "sales":
            await ctx.reply(render("boss_unclear", question=_clarify(intent)))
        case _:
            await ctx.reply(render("boss_out_of_scope"))


async def handle_bills(ctx: HandlerContext) -> None:
    await _send_bills(ctx)


async def _strip_buttons(ctx: HandlerContext, label: str) -> None:
    query = ctx.update.callback_query
    message = query.message if query else None
    message_id = getattr(message, "message_id", None)
    text = getattr(message, "text", None)
    if message_id is not None and text:
        await ctx.edit(message_id, f"{text}\n\n{label}", reply_markup=None)


async def _held(ctx: HandlerContext, entry_id: int) -> JournalEntry | None:
    entry = await ctx.session.get(
        JournalEntry, entry_id, with_for_update=True, populate_existing=True
    )
    if (
        entry is None
        or entry.status != EntryStatus.PROPOSED
        or entry.source != EntrySource.MANUAL
        or entry.invoice_id is not None
    ):
        return None
    return entry


async def _propose_payment(ctx: HandlerContext, bill_id: int) -> bool:
    bill = await ctx.session.get(Bill, bill_id, with_for_update=True)
    if bill is None or bill.status != BillStatus.OPEN:
        return False
    supplier = await ctx.session.get_one(Supplier, bill.supplier_id)
    invoice = await ctx.session.get(Invoice, bill.invoice_id) if bill.invoice_id else None
    remaining = bill.amount - bill.paid_amount
    ref = f" {invoice.invoice_no}" if invoice is not None and invoice.invoice_no else ""
    today = await business_today(ctx.session)
    lines = [
        ProposedLine("Accounts Payable", debit=remaining),
        ProposedLine("Bank", credit=remaining),
    ]
    await _propose(ctx, f"Payment {supplier.name}{ref}", today, lines, bill_id=bill.id)
    return True


async def _record_payment(ctx: HandlerContext, entry: JournalEntry, bill_id: int) -> bool:
    bill = await ctx.session.get(Bill, bill_id, with_for_update=True)
    if bill is None or bill.status != BillStatus.OPEN:
        return False
    amount = bill.amount - bill.paid_amount
    ctx.session.add(Payment(bill_id=bill.id, entry_id=entry.id, amount=amount, paid_on=entry.date))
    bill.paid_amount = bill.paid_amount + amount
    bill.status = BillStatus.PAID
    await ctx.session.flush()
    return True


async def handle_callback(ctx: HandlerContext) -> None:
    query = ctx.update.callback_query
    if query is None or query.data is None:
        return
    action, args = decode_callback(query.data)
    if not args or not all(a.isdigit() for a in args):
        await ctx.answer_callback(query.id)
        return
    first = int(args[0])
    if action == PAY:
        ok = await _propose_payment(ctx, first)
        await ctx.answer_callback(query.id, None if ok else render("boss_handled"))
        return
    entry = await _held(ctx, first)
    if entry is None:
        await ctx.answer_callback(query.id, render("boss_handled"))
        return
    await ctx.answer_callback(query.id)
    if action in (CANCEL, EDIT):
        await reject_held(ctx.session, entry.id)
        label = "Cancelled." if action == CANCEL else "Edit requested."
        await _strip_buttons(ctx, label)
        await ctx.reply(render("boss_cancelled" if action == CANCEL else "boss_edit"))
        return
    if action == PAY_CONFIRM and len(args) > 1:
        bill = await ctx.session.get(
            Bill, int(args[1]), with_for_update=True, populate_existing=True
        )
        if bill is None or bill.status != BillStatus.OPEN:
            await reject_held(ctx.session, entry.id)
            await _strip_buttons(ctx, "Cancelled.")
            await ctx.reply(render("boss_handled"))
            return
    try:
        posted = await post_held(
            ctx.session, entry.id, source=EntrySource.MANUAL, actor=AuditActor.BOSS
        )
    except LedgerError:
        log.exception("boss proposal %s refused", entry.id)
        await _strip_buttons(ctx, "Not posted.")
        await ctx.reply(render("boss_cancelled"))
        return
    if (
        action == PAY_CONFIRM
        and len(args) > 1
        and not await _record_payment(ctx, posted, int(args[1]))
    ):
        raise LedgerError(f"bill {args[1]} closed while entry {entry.id} was posting")
    entry_no = format_entry_no(posted.entry_no) if posted.entry_no is not None else ""
    await _strip_buttons(ctx, "Confirmed.")
    await ctx.reply(
        render("boss_posted", entry_no=entry_no, date=format_day(posted.date), note=posted.note)
    )


HANDLERS = (
    Handler("boss_callback", frozenset({Role.BOSS}), matches_callback, handle_callback),
    Handler("boss_bills", frozenset({Role.BOSS}), matches_bills, handle_bills),
    Handler("boss_text", frozenset({Role.BOSS}), matches_text, handle_text),
)


def register() -> None:
    """See bookkeeper/routes.py and planning/build-plan.md (verifier notes, handler order)."""
    for handler in HANDLERS:
        if handler not in registry.HANDLERS:
            registry.HANDLERS.append(handler)
