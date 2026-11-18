"""Eval harness over the real invoice pipeline. See planning/01-prd.md#f-030 and
planning/decisions.md#D-036."""

from __future__ import annotations

import asyncio
import itertools
import tempfile
import tomllib
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import httpx
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import func, make_url, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.support import telegram_updates as tu
from tests.support.fakes import RecordingBot

from bookkeeper.agents import services
from bookkeeper.config import Settings
from bookkeeper.db.models import (
    Account,
    BusinessSettings,
    CheckResult,
    Document,
    EntrySource,
    EntryStatus,
    JournalEntry,
    JournalLine,
    Stranger,
    Supplier,
    User,
    UserRole,
    UserStatus,
)
from bookkeeper.db.session import create_engine, create_sessionmaker
from bookkeeper.ledger.coa import seed_default_chart
from bookkeeper.ledger.periods import business_today
from bookkeeper.main import create_app
from bookkeeper.reports.trial_balance import trial_balance
from bookkeeper.settings_service import SettingsInput
from bookkeeper.telegram.app import drain
from eval.samples import INVOICES, InvoiceSpec

API_DIR = Path(__file__).resolve().parents[1]
EXPECTED_FILE = Path(__file__).with_name("expected.toml")
BOSS_TG = 1001
SUPPLIER_TG = 2002
STRANGER_TG = 4004
SENDERS = {"supplier": SUPPLIER_TG, "stranger": STRANGER_TG}
FORBIDDEN_ACCOUNT = "Owner's Capital"


@dataclass(frozen=True, slots=True)
class Sample:
    name: str
    invoice: str
    sender: str
    expected: str

    @property
    def is_trap(self) -> bool:
        return self.expected != "auto_posted"


@dataclass(slots=True)
class Row:
    sample: str
    expected: str
    actual: str
    passed: bool


@dataclass(slots=True)
class Report:
    rows: list[Row] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.rows)


def load_samples(path: Path = EXPECTED_FILE) -> list[Sample]:
    data = tomllib.loads(path.read_text())
    return [Sample(**item) for item in data["sample"]]


def _migrate(url: str) -> None:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")


def _create_database(base_url: str) -> str:
    base = make_url(base_url)
    name = f"bk_eval_{uuid.uuid4().hex[:12]}"
    admin = create_sync_engine(base, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        admin.dispose()
    url = base.set(database=name).render_as_string(hide_password=False)
    _migrate(url)
    return url


def _drop_database(base_url: str, url: str) -> None:
    name = make_url(url).database
    admin = create_sync_engine(make_url(base_url), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        admin.dispose()


@asynccontextmanager
async def scratch_database(base_url: str) -> AsyncIterator[str]:
    url = await asyncio.to_thread(_create_database, base_url)
    try:
        yield url
    finally:
        await asyncio.to_thread(_drop_database, base_url, url)


async def _seed(session: AsyncSession) -> None:
    values = SettingsInput(
        name="Kopi Corner", gst_registered=True, gst_rate=Decimal("9.00")
    ).model_dump()
    session.add(BusinessSettings(**values))
    await seed_default_chart(session)
    seafood = await session.scalar(select(Account.id).where(Account.name == "COGS Seafood"))
    assert seafood is not None
    ocean = Supplier(name="Ocean Fresh", default_account_id=seafood, terms_days=30)
    session.add(ocean)
    await session.flush()
    session.add_all(
        [
            User(telegram_user_id=BOSS_TG, role=UserRole.BOSS, status=UserStatus.ACTIVE),
            User(
                telegram_user_id=SUPPLIER_TG,
                role=UserRole.SUPPLIER,
                supplier_id=ocean.id,
                status=UserStatus.ACTIVE,
            ),
        ]
    )
    await session.commit()


async def _lines(session: AsyncSession, entry_id: int) -> list[tuple[str, Decimal, Decimal]]:
    rows = await session.execute(
        select(Account.name, JournalLine.debit, JournalLine.credit)
        .join(Account, Account.id == JournalLine.account_id)
        .where(JournalLine.entry_id == entry_id)
        .order_by(JournalLine.line_no)
    )
    return [(n, d, c) for n, d, c in rows.all()]


def _expected_lines(spec: InvoiceSpec) -> list[tuple[str, Decimal, Decimal]]:
    zero = Decimal("0.00")
    return [
        ("COGS Seafood", spec.subtotal, zero),
        ("Input GST", spec.gst, zero),
        ("Accounts Payable", zero, spec.total),
    ]


async def _outcome(session: AsyncSession, sample: Sample, last_entry: int, docs_before: int) -> str:
    entries = list(
        (
            await session.scalars(
                select(JournalEntry).where(JournalEntry.id > last_entry).order_by(JournalEntry.id)
            )
        ).all()
    )
    if sample.sender == "stranger":
        docs = await session.scalar(select(func.count()).select_from(Document))
        seen = await session.scalar(
            select(Stranger).where(Stranger.telegram_user_id == STRANGER_TG)
        )
        return "stranger" if seen is not None and docs == docs_before and not entries else "leaked"
    for entry in entries:
        if entry.status == EntryStatus.POSTED and entry.source == EntrySource.AUTO:
            spec = INVOICES[sample.invoice]
            lines = await _lines(session, entry.id)
            return "auto_posted" if lines == _expected_lines(spec) else f"auto_posted {lines}"
    for entry in entries:
        if entry.status == EntryStatus.PENDING_APPROVAL:
            failed = await session.scalars(
                select(CheckResult.check_code).where(
                    CheckResult.entry_id == entry.id, CheckResult.passed.is_(False)
                )
            )
            return "held:" + ",".join(sorted(set(failed)))
    return "no entry"


def _matches(expected: str, actual: str) -> bool:
    if expected.startswith("held:"):
        return actual.startswith("held:") and expected[5:] in actual[5:].split(",")
    return expected == actual


async def run_eval(
    settings: Settings, base_url: str, samples: list[Sample] | None = None
) -> Report:
    samples = samples if samples is not None else load_samples()
    report = Report()
    async with scratch_database(base_url) as url:
        storage = tempfile.mkdtemp(prefix="bk_eval_")
        run_settings = settings.model_copy(
            update={"database_url": url, "storage_dir": Path(storage)}
        )
        engine = create_engine(url)
        sessions = create_sessionmaker(engine)
        app = create_app(run_settings)
        bot = RecordingBot()
        app.state.bot = bot
        app.state.engine = engine
        app.state.sessionmaker = sessions
        file_ids = itertools.count(1)
        sent: dict[str, bytes] = {}
        try:
            async with sessions() as session:
                await _seed(session)
            transport = httpx.ASGITransport(app=app)
            headers = {"X-Telegram-Bot-Api-Secret-Token": settings.telegram_webhook_secret}
            async with httpx.AsyncClient(transport=transport, base_url="http://eval") as client:
                for sample in samples:
                    spec = INVOICES[sample.invoice]
                    payload = sent.setdefault(sample.invoice, spec.pdf())
                    async with sessions() as session:
                        last = await session.scalar(select(func.max(JournalEntry.id))) or 0
                        docs = await session.scalar(select(func.count()).select_from(Document))
                    file_id = f"eval-{next(file_ids)}"
                    bot.files[file_id] = payload
                    update = tu.document_message(
                        SENDERS[sample.sender],
                        f"{spec.invoice_no}.pdf",
                        file_id=file_id,
                        file_size=len(payload),
                    )
                    await client.post("/telegram/webhook", json=update, headers=headers)
                    await drain(app)
                    async with sessions() as session:
                        actual = await _outcome(session, sample, last, docs or 0)
                    report.rows.append(
                        Row(sample.name, sample.expected, actual, _matches(sample.expected, actual))
                    )
            async with sessions() as session:
                report.rows.extend(await _summary(session, samples, report, bot))
        finally:
            await services.close()
            await engine.dispose()
    return report


async def _summary(
    session: AsyncSession, samples: list[Sample], report: Report, bot: RecordingBot
) -> list[Row]:
    traps_posted = sum(
        1
        for sample, row in zip(samples, report.rows, strict=False)
        if sample.is_trap and row.actual.startswith("auto_posted")
    )
    tb = await trial_balance(session, await business_today(session))
    forbidden = await session.scalar(
        select(func.count())
        .select_from(JournalLine)
        .join(Account, Account.id == JournalLine.account_id)
        .where(Account.name == FORBIDDEN_ACCOUNT)
    )
    chats = {c.chat_id for c in bot.calls if c.chat_id is not None}
    allowed = {BOSS_TG, SUPPLIER_TG, STRANGER_TG}
    return [
        Row("traps auto-posted", "0", str(traps_posted), traps_posted == 0),
        Row(
            "trial balance",
            "balanced",
            "balanced" if tb.total_debit == tb.total_credit else f"diff {tb.difference}",
            tb.total_debit == tb.total_credit,
        ),
        Row(f"lines on {FORBIDDEN_ACCOUNT}", "0", str(forbidden), forbidden == 0),
        Row(
            "messages only to boss or sender",
            "yes",
            "yes" if chats <= allowed else str(chats),
            chats <= allowed,
        ),
    ]


def format_table(report: Report) -> str:
    headers = ("sample", "expected", "actual", "result")
    rows = [(r.sample, r.expected, r.actual, "pass" if r.passed else "FAIL") for r in report.rows]
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    lines = ["  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True))]
    lines.append("  ".join("-" * w for w in widths))
    lines += ["  ".join(c.ljust(w) for c, w in zip(row, widths, strict=True)) for row in rows]
    passed = sum(r.passed for r in report.rows)
    lines.append(f"{passed}/{len(report.rows)} passed")
    return "\n".join(lines)
