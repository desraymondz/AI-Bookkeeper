"""Stranger flow. See planning/01-prd.md#f-010 and planning/decisions.md#D-005."""

from __future__ import annotations

import datetime as dt
import re

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import ForceReply, Message, Update

from bookkeeper.db.models import (
    Account,
    AccountType,
    Stranger,
    StrangerDecision,
    Supplier,
    User,
    UserRole,
    UserStatus,
)
from bookkeeper.telegram import handlers as registry
from bookkeeper.telegram import notify
from bookkeeper.telegram.keyboards import Button, decode_callback, inline_keyboard
from bookkeeper.telegram.router import Handler, HandlerContext, Role, Sender
from bookkeeper.templates import render

PREVIEW_LIMIT = 200
NAME_LIMIT = 200
REF_PATTERN = re.compile(r"Ref S(\d+)")
DEFAULT_PURCHASE_CODE = "5000"


def _is_start(message: Message) -> bool:
    return bool(message.text and message.text.split(maxsplit=1)[0].split("@")[0] == "/start")


def matches_stranger_message(update: Update) -> bool:
    message = update.message
    return message is not None and not _is_start(message)


def _preview(message: Message) -> str:
    if message.document is not None:
        text = f"[document] {message.document.file_name or ''}".strip()
    elif message.photo:
        text = "[photo]"
    else:
        text = message.text or message.caption or "[message]"
    return text[:PREVIEW_LIMIT]


def _label(stranger: Stranger) -> str:
    return stranger.display_name or stranger.username or str(stranger.telegram_user_id)


async def handle_stranger_message(ctx: HandlerContext) -> None:
    message = ctx.update.message
    if message is None:
        return
    sender = ctx.sender
    now = dt.datetime.now(dt.UTC)
    inserted = (
        await ctx.session.execute(
            pg_insert(Stranger)
            .values(
                telegram_user_id=sender.telegram_user_id,
                username=sender.username,
                display_name=sender.display_name,
                first_message_preview=_preview(message),
                first_seen=now,
                last_seen=now,
            )
            .on_conflict_do_nothing(index_elements=["telegram_user_id"])
            .returning(Stranger.id)
        )
    ).scalar_one_or_none()
    if inserted is None:
        row = await ctx.session.scalar(
            select(Stranger).where(Stranger.telegram_user_id == sender.telegram_user_id)
        )
        if row is not None:
            row.last_seen = now
        return
    stranger = await ctx.session.get(Stranger, inserted)
    assert stranger is not None
    await ctx.reply(render("stranger_reply"))
    card = render(
        "stranger_card",
        who=stranger.display_name or "unknown",
        username=f"@{stranger.username}" if stranger.username else "none",
        preview=stranger.first_message_preview or "",
    )
    keyboard = inline_keyboard(
        [
            [
                Button("Ignore", "st_ign", (stranger.id,)),
                Button("Add as supplier", "st_add", (stranger.id,)),
                Button("Block", "st_blk", (stranger.id,)),
            ]
        ]
    )
    await ctx.to_boss(card, reply_markup=keyboard)


def matches_stranger_callback(update: Update) -> bool:
    query = update.callback_query
    return (
        query is not None and query.data is not None and decode_callback(query.data)[0] in _ACTIONS
    )


async def _pending(ctx: HandlerContext, stranger_id: str) -> Stranger | None:
    stranger = await ctx.session.get(Stranger, int(stranger_id))
    if stranger is None or stranger.decision is not StrangerDecision.PENDING:
        return None
    return stranger


async def _bind(session: AsyncSession, stranger: Stranger, supplier: Supplier) -> None:
    user = await session.scalar(
        select(User).where(User.telegram_user_id == stranger.telegram_user_id)
    )
    if user is None:
        user = User(telegram_user_id=stranger.telegram_user_id)
        session.add(user)
    user.username = stranger.username
    user.display_name = stranger.display_name
    user.role = UserRole.SUPPLIER
    user.supplier_id = supplier.id
    user.status = UserStatus.ACTIVE
    user.linked_at = dt.datetime.now(dt.UTC)
    stranger.decision = StrangerDecision.ADDED
    stranger.decided_at = dt.datetime.now(dt.UTC)


async def _notify_added(ctx: HandlerContext, stranger: Stranger, supplier: Supplier) -> None:
    await _bind(ctx.session, stranger, supplier)
    await ctx.session.flush()
    target = Sender(Role.SUPPLIER, stranger.telegram_user_id, supplier_id=supplier.id)
    await notify.to_sender(ctx._bot, target, render("stranger_added"))


async def _default_account_id(session: AsyncSession) -> int | None:
    preferred = await session.scalar(
        select(Account.id).where(Account.code == DEFAULT_PURCHASE_CODE)
    )
    if preferred is not None:
        return preferred
    return await session.scalar(
        select(Account.id).where(Account.type == AccountType.EXPENSE).order_by(Account.code)
    )


async def handle_stranger_callback(ctx: HandlerContext) -> None:
    query = ctx.update.callback_query
    if query is None or query.data is None or query.message is None:
        return
    action, args = decode_callback(query.data)
    message_id = query.message.message_id
    stranger = await _pending(ctx, args[0])
    if stranger is None:
        await ctx.answer_callback(query.id, "Already handled")
        return
    name = _label(stranger)
    if action in ("st_ign", "st_blk"):
        ignored = action == "st_ign"
        stranger.decision = StrangerDecision.IGNORED if ignored else StrangerDecision.BLOCKED
        stranger.decided_at = dt.datetime.now(dt.UTC)
        outcome = "ignored" if ignored else "blocked"
        await ctx.edit(message_id, render("stranger_decided", who=name, outcome=outcome))
    elif action == "st_add":
        suppliers = (
            await ctx.session.scalars(
                select(Supplier).where(Supplier.active.is_(True)).order_by(Supplier.name)
            )
        ).all()
        rows = [[Button(s.name, "st_pick", (stranger.id, s.id))] for s in suppliers]
        rows.append([Button("New supplier", "st_new", (stranger.id,))])
        await ctx.edit(
            message_id, render("stranger_pick", who=name), reply_markup=inline_keyboard(rows)
        )
    elif action == "st_pick":
        supplier = await ctx.session.get(Supplier, int(args[1]))
        if supplier is None or not supplier.active:
            await ctx.answer_callback(query.id, "Supplier not found")
            return
        await _notify_added(ctx, stranger, supplier)
        await ctx.edit(
            message_id, render("stranger_decided", who=name, outcome=f"added as {supplier.name}")
        )
    elif action == "st_new":
        await ctx.to_boss(
            render("stranger_name_prompt", who=name, stranger_id=stranger.id),
            reply_markup=ForceReply(selective=True),
        )
    await ctx.answer_callback(query.id)


def _reply_ref(update: Update) -> int | None:
    message = update.message
    if message is None or not message.text or message.reply_to_message is None:
        return None
    found = REF_PATTERN.search(message.reply_to_message.text or "")
    return int(found.group(1)) if found else None


def matches_new_supplier_name(update: Update) -> bool:
    return _reply_ref(update) is not None


async def handle_new_supplier_name(ctx: HandlerContext) -> None:
    message = ctx.update.message
    ref = _reply_ref(ctx.update)
    if message is None or message.text is None or ref is None:
        return
    stranger = await _pending(ctx, str(ref))
    name = message.text.strip()[:NAME_LIMIT]
    account_id = await _default_account_id(ctx.session)
    if stranger is None or not name or account_id is None:
        return
    supplier = Supplier(name=name, default_account_id=account_id)
    ctx.session.add(supplier)
    await ctx.session.flush()
    await _notify_added(ctx, stranger, supplier)
    await ctx.reply(render("stranger_decided", who=_label(stranger), outcome=f"added as {name}"))


_ACTIONS = frozenset({"st_ign", "st_blk", "st_add", "st_pick", "st_new"})

registry.HANDLERS.append(
    Handler(
        "stranger", frozenset({Role.STRANGER}), matches_stranger_message, handle_stranger_message
    )
)
registry.HANDLERS.append(
    Handler(
        "stranger_callback",
        frozenset({Role.BOSS}),
        matches_stranger_callback,
        handle_stranger_callback,
    )
)
registry.HANDLERS.append(
    Handler(
        "stranger_new_supplier",
        frozenset({Role.BOSS}),
        matches_new_supplier_name,
        handle_new_supplier_name,
    )
)


async def pending_strangers(session: AsyncSession) -> list[Stranger]:
    rows = await session.scalars(
        select(Stranger)
        .where(Stranger.decision == StrangerDecision.PENDING)
        .order_by(Stranger.first_seen)
    )
    return list(rows)
