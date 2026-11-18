"""Invoice pipeline graph. See planning/03-tech-stack.md#5-langgraph-layout and
planning/01-prd.md#f-014-auto-post-and-fyi, #f-015-exceptions-and-boss-approval."""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from sqlalchemy import delete, func, select
from sqlalchemy.orm import aliased
from telegram import ForceReply

from bookkeeper import audit
from bookkeeper.agents.doctext import pdf_text
from bookkeeper.agents.extract import ExtractionFailedError, extract_invoice
from bookkeeper.agents.llm import LLMClient, LLMPart
from bookkeeper.agents.prompts import REVISE_SYSTEM
from bookkeeper.agents.propose import propose_entry
from bookkeeper.agents.schemas import ExtractedInvoice, InvoiceRevision
from bookkeeper.agents.tool_gate import ToolCall, run_tool_call
from bookkeeper.db.models import (
    Account,
    AccountType,
    Approval,
    AuditActor,
    Bill,
    BusinessSettings,
    Document,
    EntryKind,
    EntrySource,
    EntryStatus,
    Invoice,
    InvoiceLine,
    JournalEntry,
    JournalLine,
    Supplier,
    User,
)
from bookkeeper.db.models import CheckResult as CheckRow
from bookkeeper.ledger import (
    LedgerError,
    format_entry_no,
    hold_entry,
    post_held,
    reject_held,
    reverse,
    revise_held,
)
from bookkeeper.ledger.checks import CheckContext, run_checks, store_results
from bookkeeper.ledger.checks.price_change import normalize_item
from bookkeeper.ledger.money import ZERO, format_money
from bookkeeper.ledger.periods import format_day
from bookkeeper.reports.trial_balance import trial_balance
from bookkeeper.telegram.keyboards import Button, inline_keyboard
from bookkeeper.telegram.router import HandlerContext
from bookkeeper.templates import render

TB_CODE = "trial_balance"
TITLES = {
    "known_supplier": "Supplier",
    "arithmetic": "Arithmetic",
    "gst": "GST",
    "balanced": "Balance",
    "duplicate": "Duplicate",
    "revision": "Revised invoice",
    "price_change": "Price change",
    "period": "Period",
    "sanity": "Sanity",
    "suspicious": "Suspicious content",
    TB_CODE: "Trial balance",
}
_AMOUNT = r"(\d[\d,]*\.\d{2})"
_GST_DETAIL = re.compile(
    rf"GST should be {_AMOUNT} \(([\d.]+)% of {_AMOUNT}\), invoice says {_AMOUNT}"
)
APPROVE, EDIT, REJECT = "approve", "edit", "reject"
IGNORE_DUPLICATE, POST_ANYWAY = "ignore_duplicate", "post_anyway"


class InvoiceState(TypedDict, total=False):
    document_id: int
    invoice_id: int
    entry_id: int | None
    kind: str
    outcome: str
    decision: str | None
    edit_text: str | None
    edited: bool
    tell_supplier: bool


class TrialBalanceImbalanceError(Exception):
    def __init__(self, difference: Decimal) -> None:
        super().__init__(f"trial balance off by {difference}")
        self.difference = difference


async def tb_difference(session: Any) -> Decimal:
    report = await trial_balance(session, dt.date.max)
    return report.difference


def plain_words(code: str, detail: str) -> str:
    if code == "gst":
        match = _GST_DETAIL.search(detail)
        if match:
            expected, rate, subtotal, said = match.groups()
            return f"GST is {said} but {rate}% of {subtotal} is {expected}."
    return detail


def thread_id(invoice_id: int) -> str:
    return f"invoice:{invoice_id}"


class InvoiceFlow:
    def __init__(self, ctx: HandlerContext, llm: LLMClient) -> None:
        self.ctx = ctx
        self.session = ctx.session
        self.llm = llm

    async def _settings(self) -> BusinessSettings:
        row = await self.session.scalar(select(BusinessSettings).order_by(BusinessSettings.id))
        if row is None:
            raise RuntimeError("Business settings are not set up")
        return row

    async def _invoice(self, state: InvoiceState) -> Invoice:
        return await self.session.get_one(Invoice, state["invoice_id"])

    async def _names(self, entry_id: int) -> list[tuple[str, Decimal, Decimal]]:
        rows = await self.session.execute(
            select(Account.name, JournalLine.debit, JournalLine.credit)
            .join(JournalLine, JournalLine.account_id == Account.id)
            .where(JournalLine.entry_id == entry_id)
            .order_by(JournalLine.line_no)
        )
        return [(n, d, c) for n, d, c in rows.all()]

    async def _stop_unreadable(self, supplier: str, fields: str, invoice_id: int) -> InvoiceState:
        await self.ctx.to_boss(render("invoice_unreadable", supplier=supplier, fields=fields))
        audit.record(
            self.session,
            AuditActor.AGENT,
            "invoice.unreadable",
            "invoice",
            invoice_id,
            {"fields": fields},
        )
        await self.session.commit()
        return {"outcome": "stop"}

    async def extract(self, state: InvoiceState) -> InvoiceState:
        invoice = await self._invoice(state)
        document = await self.session.get_one(Document, state["document_id"])
        sender = await self.session.get(User, document.sender_user_id or 0)
        supplier = await self.session.get(Supplier, sender.supplier_id or 0) if sender else None
        name = supplier.name if supplier else "an unknown sender"
        path = Path(self.ctx.settings.storage_dir) / document.path
        data = path.read_bytes()
        try:
            extraction = await extract_invoice(self.llm, data=data, mime=document.mime)
        except ExtractionFailedError as exc:
            audit.record(
                self.session,
                AuditActor.AGENT,
                "invoice.extraction_failed",
                "document",
                document.id,
                {"attempts": exc.attempts, "error": exc.last_error},
            )
            return await self._stop_unreadable(name, "document", invoice.id)

        found = extraction.invoice
        invoice.supplier_id = supplier.id if supplier else None
        invoice.invoice_no = found.invoice_no
        invoice.invoice_date = found.invoice_date
        invoice.due_date = found.due_date
        invoice.currency = found.currency
        invoice.subtotal = found.subtotal
        invoice.gst = found.gst
        invoice.total = found.total
        invoice.confidence = found.confidence
        invoice.model = extraction.model
        invoice.extraction_json = {"extracted": found.model_dump(mode="json")}
        await self.session.execute(delete(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id))
        self.session.add_all(
            InvoiceLine(
                invoice_id=invoice.id,
                line_no=number,
                description=line.description or "",
                normalized_item=normalize_item(line.description) or None,
                qty=line.qty,
                unit=line.unit,
                unit_price=line.unit_price,
                line_total=line.line_total,
            )
            for number, line in enumerate(found.lines, start=1)
        )
        audit.record(
            self.session,
            AuditActor.AGENT,
            "invoice.extracted",
            "document",
            document.id,
            {
                "invoice_id": invoice.id,
                "attempts": extraction.attempts,
                "missing": found.missing_required,
                "confidence": str(found.confidence),
            },
            model=extraction.model,
        )
        await self.session.flush()
        missing = list(found.missing_required)
        if found.invoice_date is None:
            missing.append("invoice_date")
        if supplier is None:
            return await self._stop_unreadable(name, "sender", invoice.id)
        if missing:
            labels = {"invoice_no": "invoice number", "total": "total", "invoice_date": "date"}
            return await self._stop_unreadable(
                supplier.name, " and ".join(labels[m] for m in missing), invoice.id
            )
        return {"outcome": "go"}

    async def _revision_original(self, invoice: Invoice) -> JournalEntry | None:
        if not invoice.invoice_no or invoice.supplier_id is None:
            return None
        prior = select(Invoice.id).where(
            Invoice.supplier_id == invoice.supplier_id,
            func.lower(func.btrim(Invoice.invoice_no)) == invoice.invoice_no.strip().lower(),
            Invoice.document_id != invoice.document_id,
            Invoice.id != invoice.id,
        )
        reversal = aliased(JournalEntry)
        reversed_already = (
            select(reversal.id)
            .where(
                reversal.reverses_id == JournalEntry.id,
                reversal.kind == EntryKind.REVERSAL,
                reversal.status == EntryStatus.POSTED,
            )
            .exists()
        )
        return await self.session.scalar(
            select(JournalEntry)
            .where(
                JournalEntry.invoice_id.in_(prior),
                JournalEntry.status == EntryStatus.POSTED,
                JournalEntry.kind == EntryKind.NORMAL,
                ~reversed_already,
            )
            .order_by(JournalEntry.id.desc())
            .limit(1)
        )

    async def evaluate(self, state: InvoiceState) -> InvoiceState:
        invoice = await self._invoice(state)
        document = await self.session.get_one(Document, invoice.document_id)
        sender = await self.session.get_one(User, document.sender_user_id or 0)
        supplier = await self.session.get_one(Supplier, invoice.supplier_id or 0)
        settings = await self._settings()
        extracted = ExtractedInvoice.model_validate(invoice.extraction_json["extracted"])
        assert invoice.model is not None
        proposal = await propose_entry(
            self.session,
            extracted,
            supplier=supplier,
            settings=settings,
            model=invoice.model,
            ref_type="invoice",
            ref_id=invoice.id,
        )
        draft = replace(proposal.draft, invoice_id=invoice.id)
        override = invoice.extraction_json.get("expense_account_id")
        if override is not None:
            lines = list(draft.lines)
            lines[0] = replace(lines[0], account_id=int(override))
            draft = replace(draft, lines=lines)

        data = (Path(self.ctx.settings.storage_dir) / document.path).read_bytes()
        layer = await pdf_text(data, document.mime)
        text = "\n".join(part for part in (layer, extracted.other_text) if part) or None
        results = await run_checks(
            CheckContext(
                session=self.session,
                settings=settings,
                supplier=supplier,
                sender_user=sender,
                invoice=extracted,
                document=document,
                proposed_entry=draft,
                current_invoice_id=invoice.id,
                document_text=text,
            )
        )
        failed = {r.code for r in results if not r.passed}
        kind = "normal"
        original: JournalEntry | None = None
        if "duplicate" in failed:
            kind = "duplicate"
        elif "revision" in failed:
            original = await self._revision_original(invoice)
            if original is not None:
                kind = "revision"
                draft = replace(draft, reverses_id=original.id)

        entry_id = state.get("entry_id")
        if entry_id is None:
            entry = await hold_entry(self.session, draft, actor=AuditActor.AGENT)
            entry_id = entry.id
        else:
            await revise_held(self.session, entry_id, draft, actor=AuditActor.AGENT)
            await self.session.execute(delete(CheckRow).where(CheckRow.entry_id == entry_id))
        await store_results(self.session, entry_id, results)
        for result in results:
            audit.record(
                self.session,
                AuditActor.AGENT,
                f"check.{result.code}",
                "journal_entry",
                entry_id,
                {"passed": result.passed, "detail": result.detail, "invoice_id": invoice.id},
            )
        await self.session.flush()
        return {
            "entry_id": entry_id,
            "kind": kind,
            "outcome": "pass" if not failed else "fail",
        }

    async def _bill(
        self, invoice: Invoice, supplier: Supplier, original: JournalEntry | None
    ) -> None:
        assert invoice.total is not None
        assert invoice.invoice_date is not None
        due = invoice.due_date or invoice.invoice_date + dt.timedelta(days=supplier.terms_days)
        bill: Bill | None = None
        if original is not None and original.invoice_id is not None:
            bill = await self.session.scalar(
                select(Bill).where(Bill.invoice_id == original.invoice_id)
            )
        if bill is None:
            self.session.add(
                Bill(
                    invoice_id=invoice.id,
                    supplier_id=supplier.id,
                    amount=invoice.total,
                    due_date=due,
                )
            )
        else:
            bill.invoice_id = invoice.id
            bill.amount = invoice.total
            bill.due_date = due
        await self.session.flush()

    async def post(self, state: InvoiceState) -> InvoiceState:
        invoice = await self._invoice(state)
        supplier = await self.session.get_one(Supplier, invoice.supplier_id or 0)
        entry_id = state["entry_id"]
        assert entry_id is not None
        decision = state.get("decision")
        source = EntrySource.AUTO if decision is None else EntrySource.BOSS_APPROVED
        actor = AuditActor.AGENT if decision is None else AuditActor.BOSS
        held = await self.session.get_one(JournalEntry, entry_id, populate_existing=True)
        original = (
            await self.session.get(JournalEntry, held.reverses_id) if held.reverses_id else None
        )
        try:
            async with self.session.begin_nested():
                if original is not None:
                    await reverse(self.session, original.id, source=source, actor=actor)
                entry = await post_held(self.session, entry_id, source=source, actor=actor)
                await self._bill(invoice, supplier, original)
                difference = await tb_difference(self.session)
                if difference != ZERO:
                    raise TrialBalanceImbalanceError(difference)
        except TrialBalanceImbalanceError as exc:
            await self.session.refresh(held)
            self.session.add(
                CheckRow(
                    entry_id=entry_id,
                    check_code=TB_CODE,
                    passed=False,
                    detail=(
                        f"Trial balance is off by {format_money(abs(exc.difference))} after "
                        "posting; the posting and its bill were rolled back."
                    ),
                )
            )
            audit.record(
                self.session,
                AuditActor.SYSTEM,
                "posting.rolled_back",
                "journal_entry",
                entry_id,
                {"difference": str(exc.difference)},
            )
            await self.session.flush()
            return {"outcome": "tb_failed", "kind": "normal"}
        except LedgerError as exc:
            audit.record(
                self.session,
                AuditActor.SYSTEM,
                "posting.refused",
                "journal_entry",
                entry_id,
                {"error": str(exc)},
            )
            await self.ctx.to_boss(
                render(
                    "invoice_post_refused",
                    supplier=supplier.name,
                    invoice_no=invoice.invoice_no,
                    reason=str(exc).rstrip("."),
                )
            )
            await self.session.commit()
            return {"outcome": "stop"}

        assert entry.entry_no is not None
        lines = await self._names(entry.id)
        if decision is None:
            due = invoice.due_date or invoice.invoice_date
            if invoice.due_date is None and invoice.invoice_date is not None:
                due = invoice.invoice_date + dt.timedelta(days=supplier.terms_days)
            assert due is not None
            assert invoice.total is not None
            text = render(
                "invoice_fyi",
                supplier=supplier.name,
                invoice_no=invoice.invoice_no,
                total=format_money(invoice.total),
                due=format_day(due),
                debits=", ".join(f"{n} {format_money(d)}" for n, d, _c in lines if d > 0),
                credits=", ".join(f"{n} {format_money(c)}" for n, _d, c in lines if c > 0),
            )
            await self.ctx.to_boss(text)
            audit.record(
                self.session,
                AuditActor.AGENT,
                "fyi.sent",
                "journal_entry",
                entry.id,
                {"invoice_id": invoice.id, "entry_no": format_entry_no(entry.entry_no)},
            )
        else:
            await self.ctx.to_boss(
                render(
                    "invoice_posted",
                    entry_no=format_entry_no(entry.entry_no),
                    supplier=supplier.name,
                    invoice_no=invoice.invoice_no,
                )
            )
        await self.session.commit()
        return {"outcome": "done"}

    async def send_card(self, state: InvoiceState) -> InvoiceState:
        invoice = await self._invoice(state)
        supplier = await self.session.get_one(Supplier, invoice.supplier_id or 0)
        entry_id = state["entry_id"]
        assert entry_id is not None
        entry = await self.session.get_one(JournalEntry, entry_id, populate_existing=True)
        failed = (
            await self.session.scalars(
                select(CheckRow)
                .where(CheckRow.entry_id == entry_id, CheckRow.passed.is_(False))
                .order_by(CheckRow.id)
            )
        ).all()
        kind = state.get("kind", "normal")
        heading = {
            "duplicate": "Possible duplicate invoice",
            "revision": "Revised invoice",
        }.get(kind, "Invoice needs your approval")
        if any(row.check_code == TB_CODE for row in failed):
            heading = "Posting rolled back, needs your approval"
        comparison = None
        if kind == "revision" and entry.reverses_id is not None:
            original = await self.session.get_one(JournalEntry, entry.reverses_id)
            old = await self.session.get(Invoice, original.invoice_id or 0)
            if old is not None and old.total is not None and invoice.total is not None:
                label = format_entry_no(original.entry_no) if original.entry_no else "earlier"
                comparison = (
                    f"Old total {format_money(old.total)} ({label}), "
                    f"new total {format_money(invoice.total)}."
                )
        lines = await self._names(entry_id)
        text = render(
            "invoice_card",
            heading=heading,
            supplier=supplier.name,
            invoice_no=invoice.invoice_no,
            total=format_money(invoice.total or ZERO),
            reasons=[
                f"{TITLES.get(r.check_code, r.check_code)}: "
                f"{plain_words(r.check_code, r.detail or '')}"
                for r in failed
            ],
            comparison=comparison,
            date=format_day(entry.date),
            entry_lines=[
                f"Dr {n} {format_money(d)}" if d > 0 else f"Cr {n} {format_money(c)}"
                for n, d, c in lines
            ],
        )
        if kind == "duplicate":
            buttons = [
                Button("Ignore duplicate", "ap_ig", (entry_id,)),
                Button("Post anyway", "ap_pa", (entry_id,)),
            ]
        else:
            buttons = [
                Button("Approve", "ap_ok", (entry_id,)),
                Button("Edit", "ap_ed", (entry_id,)),
                Button("Reject", "ap_rj", (entry_id,)),
            ]
        sent = await self.ctx.to_boss(text, reply_markup=inline_keyboard([buttons]))
        self.session.add(
            Approval(
                entry_id=entry_id,
                telegram_message_id=getattr(sent, "message_id", None),
            )
        )
        audit.record(
            self.session,
            AuditActor.AGENT,
            "card.sent",
            "journal_entry",
            entry_id,
            {"kind": kind, "failed": [r.check_code for r in failed]},
        )
        await self.session.commit()
        return {"decision": None}

    async def wait_decision(self, state: InvoiceState) -> InvoiceState:
        value: dict[str, Any] = interrupt({"entry_id": state.get("entry_id")})
        return {"decision": value["decision"]}

    async def prompt_edit(self, state: InvoiceState) -> InvoiceState:
        await self.ctx.to_boss(
            render("invoice_edit_prompt"), reply_markup=ForceReply(selective=True)
        )
        await self.session.commit()
        return {}

    async def wait_edit(self, state: InvoiceState) -> InvoiceState:
        value: dict[str, Any] = interrupt({"edit_for": state.get("entry_id")})
        return {"edit_text": value["text"]}

    async def _apply_revision(self, invoice_id: int, revision: dict[str, Any]) -> str | None:
        invoice = await self.session.get_one(Invoice, invoice_id)
        change = InvoiceRevision.model_validate(revision)
        extracted = ExtractedInvoice.model_validate(invoice.extraction_json["extracted"])
        updates = {
            key: getattr(change, key)
            for key in ("invoice_no", "invoice_date", "due_date", "subtotal", "gst", "total")
            if getattr(change, key) is not None
        }
        extracted = extracted.model_copy(update=updates)
        payload: dict[str, Any] = {"extracted": extracted.model_dump(mode="json")}
        if change.expense_account:
            wanted = " ".join(change.expense_account.lower().split())
            accounts = (
                await self.session.scalars(
                    select(Account).where(
                        Account.type == AccountType.EXPENSE, Account.active.is_(True)
                    )
                )
            ).all()
            match = next((a for a in accounts if a.name.lower() == wanted), None)
            if match is None:
                return f"there is no expense account called {change.expense_account}."
            payload["expense_account_id"] = match.id
        elif "expense_account_id" in invoice.extraction_json:
            payload["expense_account_id"] = invoice.extraction_json["expense_account_id"]
        invoice.extraction_json = payload
        invoice.invoice_no = extracted.invoice_no
        invoice.invoice_date = extracted.invoice_date
        invoice.due_date = extracted.due_date
        invoice.subtotal = extracted.subtotal
        invoice.gst = extracted.gst
        invoice.total = extracted.total
        await self.session.flush()
        return None

    async def revise(self, state: InvoiceState) -> InvoiceState:
        invoice = await self._invoice(state)
        current = json.dumps(invoice.extraction_json.get("extracted", {}))
        failure: str | None = None
        revision: InvoiceRevision | None = None
        try:
            result = await self.llm.generate(
                task="revise",
                system=REVISE_SYSTEM,
                parts=[
                    LLMPart.from_text(f"Current invoice values:\n{current}"),
                    LLMPart.from_text(f"Boss message:\n{state.get('edit_text') or ''}"),
                ],
                schema=InvoiceRevision,
            )
            if isinstance(result.parsed, InvoiceRevision):
                revision = result.parsed
            elif result.text:
                revision = InvoiceRevision.model_validate_json(result.text)
        except Exception as exc:
            failure = f"I could not understand that ({type(exc).__name__})."
        if revision is None and failure is None:
            failure = "I could not understand that."
        if revision is not None:
            outcome = await run_tool_call(
                self.session,
                self.ctx.sender,
                ToolCall(
                    "apply_revision", {"invoice_id": invoice.id, "revision": revision.model_dump()}
                ),
                {"apply_revision": self._apply_revision},
            )
            failure = outcome.value if outcome.ran else "that is not allowed."
        audit.record(
            self.session,
            AuditActor.AGENT,
            "invoice.revised" if failure is None else "invoice.revise_failed",
            "invoice",
            invoice.id,
            {"error": failure, "instruction": state.get("edit_text")},
            model=self.ctx.settings.gemini_model_revise,
        )
        if failure is not None:
            await self.ctx.to_boss(render("invoice_edit_failed", reason=failure))
            await self.session.commit()
            return {"outcome": "revise_failed"}
        return {"outcome": "revised", "edited": True}

    async def _supplier_and_invoice(self, state: InvoiceState) -> tuple[Supplier, Invoice]:
        invoice = await self._invoice(state)
        return await self.session.get_one(Supplier, invoice.supplier_id or 0), invoice

    async def ignore(self, state: InvoiceState) -> InvoiceState:
        supplier, invoice = await self._supplier_and_invoice(state)
        await reject_held(self.session, state["entry_id"] or 0, actor=AuditActor.BOSS)
        await self.ctx.to_boss(
            render("invoice_ignored", supplier=supplier.name, invoice_no=invoice.invoice_no)
        )
        await self.session.commit()
        return {}

    async def reject(self, state: InvoiceState) -> InvoiceState:
        supplier, invoice = await self._supplier_and_invoice(state)
        entry_id = state["entry_id"] or 0
        await reject_held(self.session, entry_id, actor=AuditActor.BOSS)
        await self.ctx.to_boss(
            render("invoice_rejected_ask", supplier=supplier.name, invoice_no=invoice.invoice_no),
            reply_markup=inline_keyboard(
                [[Button("Yes", "ap_ty", (entry_id,)), Button("No", "ap_tn", (entry_id,))]]
            ),
        )
        await self.session.commit()
        return {}

    async def wait_notify(self, state: InvoiceState) -> InvoiceState:
        value: dict[str, Any] = interrupt({"tell_supplier_for": state.get("entry_id")})
        return {"tell_supplier": bool(value["tell"])}

    async def notify_supplier(self, state: InvoiceState) -> InvoiceState:
        invoice = await self._invoice(state)
        told = bool(state.get("tell_supplier"))
        if told and invoice.supplier_id is not None:
            await self.ctx.to_supplier(invoice.supplier_id, render("invoice_rejected_supplier"))
            audit.record(
                self.session,
                AuditActor.AGENT,
                "supplier.notified",
                "invoice",
                invoice.id,
                {"supplier_id": invoice.supplier_id},
            )
        await self.ctx.to_boss(render("invoice_rejected_done", told=told))
        await self.session.commit()
        return {}


def _after_extract(state: InvoiceState) -> str:
    return "evaluate" if state.get("outcome") == "go" else END


def _after_evaluate(state: InvoiceState) -> str:
    if state.get("outcome") == "pass" and not state.get("edited"):
        return "post"
    return "send_card"


def _after_post(state: InvoiceState) -> str:
    return "send_card" if state.get("outcome") == "tb_failed" else END


def _after_decision(state: InvoiceState) -> str:
    return {
        APPROVE: "post",
        POST_ANYWAY: "post",
        IGNORE_DUPLICATE: "ignore",
        REJECT: "reject",
        EDIT: "prompt_edit",
    }.get(state.get("decision") or "", END)


def _after_revise(state: InvoiceState) -> str:
    return "evaluate" if state.get("outcome") == "revised" else "send_card"


def build_graph(ctx: HandlerContext, llm: LLMClient, checkpointer: BaseCheckpointSaver[Any]) -> Any:
    flow = InvoiceFlow(ctx, llm)
    graph: StateGraph[InvoiceState] = StateGraph(InvoiceState)
    for name in (
        "extract",
        "evaluate",
        "post",
        "send_card",
        "wait_decision",
        "prompt_edit",
        "wait_edit",
        "revise",
        "ignore",
        "reject",
        "wait_notify",
        "notify_supplier",
    ):
        graph.add_node(name, getattr(flow, name))
    graph.add_edge(START, "extract")
    graph.add_conditional_edges("extract", _after_extract, ["evaluate", END])
    graph.add_conditional_edges("evaluate", _after_evaluate, ["post", "send_card"])
    graph.add_conditional_edges("post", _after_post, ["send_card", END])
    graph.add_edge("send_card", "wait_decision")
    graph.add_conditional_edges(
        "wait_decision", _after_decision, ["post", "ignore", "reject", "prompt_edit", END]
    )
    graph.add_edge("prompt_edit", "wait_edit")
    graph.add_edge("wait_edit", "revise")
    graph.add_conditional_edges("revise", _after_revise, ["evaluate", "send_card"])
    graph.add_edge("ignore", END)
    graph.add_edge("reject", "wait_notify")
    graph.add_edge("wait_notify", "notify_supplier")
    graph.add_edge("notify_supplier", END)
    return graph.compile(checkpointer=checkpointer)
