"""See planning/decisions.md#D-031."""

import itertools
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.agents.llm import LLMResult
from bookkeeper.agents.schemas import ExtractedInvoice, InvoiceRevision
from bookkeeper.db.models import Bill, EntryStatus, JournalEntry
from tests.integration.telegram.conftest import BOSS_ID, SUPPLIER_ID, post_update
from tests.support import telegram_updates as tu
from tests.support.fakes import BotCall, FakeLLMClient, RecordingBot

_files = itertools.count(1)


def pdf_with_text(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 11 Tf 40 700 Td ({escaped}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(out)


def extraction(invoice: ExtractedInvoice, model: str = "fake-flash") -> LLMResult:
    return LLMResult(parsed=invoice, model=model)


def revision(**fields: Any) -> LLMResult:
    values: dict[str, Any] = {
        "invoice_no": None,
        "invoice_date": None,
        "due_date": None,
        "subtotal": None,
        "gst": None,
        "total": None,
        "expense_account": None,
    }
    return LLMResult(parsed=InvoiceRevision(**{**values, **fields}), model="fake-flash")


@dataclass
class Env:
    client: httpx.AsyncClient
    app: FastAPI
    bot: RecordingBot
    llm: FakeLLMClient
    session: AsyncSession

    async def send(
        self,
        invoice: ExtractedInvoice,
        *,
        data: bytes | None = None,
        text: str | None = None,
    ) -> bytes:
        payload = data or pdf_with_text(text or f"{invoice.invoice_no} {next(_files)}")
        self.llm.queue("extract", extraction(invoice))
        await self.send_file(payload)
        return payload

    async def send_file(self, payload: bytes) -> None:
        file_id = f"file-{next(_files)}"
        self.bot.files[file_id] = payload
        update = tu.document_message(
            SUPPLIER_ID, "inv.pdf", file_id=file_id, file_size=len(payload)
        )
        await post_update(self.client, self.app, update)

    async def press(self, data: str, user_id: int = BOSS_ID) -> None:
        await post_update(self.client, self.app, tu.callback_query(user_id, data, message_id=7))

    async def say(self, text: str, user_id: int = BOSS_ID) -> None:
        await post_update(self.client, self.app, tu.text_message(user_id, text))

    def to_boss(self) -> list[BotCall]:
        return [c for c in self.bot.calls_for("send_message") if c.chat_id == BOSS_ID]

    def to_supplier(self) -> list[BotCall]:
        return [c for c in self.bot.calls_for("send_message") if c.chat_id == SUPPLIER_ID]

    def card(self) -> BotCall:
        cards = [c for c in self.to_boss() if c.reply_markup is not None]
        return cards[-1]

    def buttons(self) -> dict[str, str]:
        markup = self.card().reply_markup
        return {b.text: b.callback_data for row in markup.inline_keyboard for b in row}

    async def entries(self, *statuses: EntryStatus) -> list[JournalEntry]:
        stmt = select(JournalEntry).order_by(JournalEntry.id)
        if statuses:
            stmt = stmt.where(JournalEntry.status.in_(statuses))
        return list((await self.session.scalars(stmt)).all())

    async def bills(self) -> list[Bill]:
        return list((await self.session.scalars(select(Bill).order_by(Bill.id))).all())
