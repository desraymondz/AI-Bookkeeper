"""See planning/01-prd.md#data-model-sketch and planning/03-tech-stack.md section 3."""

import datetime as dt
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

Money = Numeric(14, 2, asdecimal=True)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {  # noqa: RUF012
        Decimal: Money,
        dt.datetime: DateTime(timezone=True),
        dict[str, Any]: JSONB,
        list[Any]: JSONB,
    }


def _enum(enum_cls: type[StrEnum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        validate_strings=True,
        values_callable=lambda members: [m.value for m in members],
    )


def _created_at() -> Mapped[dt.datetime]:
    return mapped_column(server_default=func.now())


class UserRole(StrEnum):
    BOSS = "boss"
    SUPPLIER = "supplier"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    BLOCKED = "blocked"


class StrangerDecision(StrEnum):
    PENDING = "pending"
    IGNORED = "ignored"
    BLOCKED = "blocked"
    ADDED = "added"


class LinkPurpose(StrEnum):
    BOSS = "boss"
    SUPPLIER = "supplier"


class AccountType(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"
    CONTRA_ASSET = "contra_asset"


class DocumentKind(StrEnum):
    INVOICE = "invoice"
    SALES = "sales"
    EXCEL = "excel"


class EntryStatus(StrEnum):
    PROPOSED = "proposed"
    PENDING_APPROVAL = "pending_approval"
    POSTED = "posted"
    REJECTED = "rejected"


class EntryKind(StrEnum):
    NORMAL = "normal"
    ADJUSTING = "adjusting"
    OPENING = "opening"
    REVERSAL = "reversal"
    CLOSING = "closing"


class EntrySource(StrEnum):
    AUTO = "auto"
    BOSS_APPROVED = "boss_approved"
    MANUAL = "manual"
    SYSTEM = "system"


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"
    IGNORE_DUPLICATE = "ignore_duplicate"
    POST_ANYWAY = "post_anyway"


class BillStatus(StrEnum):
    OPEN = "open"
    PAID = "paid"


class PeriodStatus(StrEnum):
    OPEN = "open"
    CLOSING = "closing"
    LOCKED = "locked"


class AuditActor(StrEnum):
    AGENT = "agent"
    BOSS = "boss"
    SYSTEM = "system"


class BusinessSettings(Base):
    __tablename__ = "business_settings"
    __table_args__ = (
        CheckConstraint("fy_start_month BETWEEN 1 AND 12", name="fy_start_month_range"),
        CheckConstraint("gst_rate >= 0 AND gst_rate <= 100", name="gst_rate_range"),
        CheckConstraint("report_day BETWEEN 1 AND 28", name="report_day_range"),
        CheckConstraint("dup_window_days >= 0", name="dup_window_days_nonneg"),
        CheckConstraint("reminder_days >= 0", name="reminder_days_nonneg"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    currency: Mapped[str] = mapped_column(String(3), server_default="SGD")
    timezone: Mapped[str] = mapped_column(String(64), server_default="Asia/Singapore")
    fy_start_month: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    gst_registered: Mapped[bool] = mapped_column(server_default="false")
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="9.00")
    price_rule: Mapped[str] = mapped_column(String(32), server_default="any_change")
    dup_window_days: Mapped[int] = mapped_column(Integer, server_default="180")
    reminder_days: Mapped[int] = mapped_column(Integer, server_default="3")
    recap_time: Mapped[dt.time] = mapped_column(Time, server_default="21:00")
    report_day: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    report_time: Mapped[dt.time] = mapped_column(Time, server_default="09:00")
    created_at: Mapped[dt.datetime] = _created_at()
    updated_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[AccountType] = mapped_column(_enum(AccountType, "account_type"))
    subtype: Mapped[str | None] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(server_default="true")
    created_at: Mapped[dt.datetime] = _created_at()


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (CheckConstraint("terms_days >= 0", name="terms_days_nonneg"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    uen: Mapped[str | None] = mapped_column(String(32))
    default_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    terms_days: Mapped[int] = mapped_column(Integer, server_default="30")
    telegram_username_hint: Mapped[str | None] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(server_default="true")
    created_at: Mapped[dt.datetime] = _created_at()


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(role = 'supplier') = (supplier_id IS NOT NULL)", name="supplier_link_matches_role"
        ),
        Index(
            "uq_users_one_active_boss",
            "role",
            unique=True,
            postgresql_where=text("role = 'boss' AND status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64))
    display_name: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[UserRole] = mapped_column(_enum(UserRole, "user_role"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    status: Mapped[UserStatus] = mapped_column(
        _enum(UserStatus, "user_status"), server_default=UserStatus.ACTIVE.value
    )
    linked_at: Mapped[dt.datetime | None]
    created_at: Mapped[dt.datetime] = _created_at()


class Stranger(Base):
    __tablename__ = "strangers"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64))
    display_name: Mapped[str | None] = mapped_column(String(200))
    first_message_preview: Mapped[str | None] = mapped_column(Text)
    first_seen: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    last_seen: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    decision: Mapped[StrangerDecision] = mapped_column(
        _enum(StrangerDecision, "stranger_decision"),
        server_default=StrangerDecision.PENDING.value,
    )
    decided_at: Mapped[dt.datetime | None]


class LinkToken(Base):
    __tablename__ = "link_tokens"
    __table_args__ = (
        CheckConstraint(
            "(purpose = 'supplier') = (supplier_id IS NOT NULL)",
            name="supplier_link_matches_purpose",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    purpose: Mapped[LinkPurpose] = mapped_column(_enum(LinkPurpose, "link_purpose"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    expires_at: Mapped[dt.datetime]
    used_at: Mapped[dt.datetime | None]
    used_by_telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[dt.datetime] = _created_at()


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (CheckConstraint("size >= 0", name="size_nonneg"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(Text)
    preview_path: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    mime: Mapped[str] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(BigInteger)
    sender_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    received_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    kind: Mapped[DocumentKind] = mapped_column(_enum(DocumentKind, "document_kind"))


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), index=True)
    invoice_no: Mapped[str | None] = mapped_column(String(64))
    invoice_date: Mapped[dt.date | None]
    due_date: Mapped[dt.date | None]
    currency: Mapped[str | None] = mapped_column(String(3))
    subtotal: Mapped[Decimal | None]
    gst: Mapped[Decimal | None]
    total: Mapped[Decimal | None]
    extraction_json: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    model: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = _created_at()


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    line_no: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    normalized_item: Mapped[str | None] = mapped_column(String(200))
    qty: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    unit: Mapped[str | None] = mapped_column(String(32))
    unit_price: Mapped[Decimal | None]
    line_total: Mapped[Decimal | None]


class Period(Base):
    __tablename__ = "periods"
    __table_args__ = (
        UniqueConstraint("year", "month"),
        CheckConstraint("month BETWEEN 1 AND 12", name="month_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(SmallInteger)
    month: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[PeriodStatus] = mapped_column(
        _enum(PeriodStatus, "period_status"), server_default=PeriodStatus.OPEN.value
    )
    closed_at: Mapped[dt.datetime | None]


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_no: Mapped[int | None] = mapped_column(Integer, unique=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[EntrySource] = mapped_column(_enum(EntrySource, "entry_source"))
    status: Mapped[EntryStatus] = mapped_column(
        _enum(EntryStatus, "entry_status"), server_default=EntryStatus.PROPOSED.value
    )
    kind: Mapped[EntryKind] = mapped_column(
        _enum(EntryKind, "entry_kind"), server_default=EntryKind.NORMAL.value
    )
    reverses_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), index=True)
    period_id: Mapped[int | None] = mapped_column(ForeignKey("periods.id"))
    note: Mapped[str | None] = mapped_column(Text)
    posted_at: Mapped[dt.datetime | None]
    created_at: Mapped[dt.datetime] = _created_at()


class JournalLine(Base):
    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)", name="one_side_positive"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="CASCADE"), index=True
    )
    line_no: Mapped[int] = mapped_column(Integer)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    debit: Mapped[Decimal] = mapped_column(server_default="0")
    credit: Mapped[Decimal] = mapped_column(server_default="0")
    memo: Mapped[str | None] = mapped_column(Text)


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="CASCADE"), index=True
    )
    check_code: Mapped[str] = mapped_column(String(32))
    passed: Mapped[bool]
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = _created_at()


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    decision: Mapped[ApprovalDecision | None] = mapped_column(
        _enum(ApprovalDecision, "approval_decision")
    )
    decided_at: Mapped[dt.datetime | None]
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = _created_at()


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("paid_amount >= 0 AND paid_amount <= amount", name="paid_amount_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), unique=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    amount: Mapped[Decimal]
    due_date: Mapped[dt.date]
    paid_amount: Mapped[Decimal] = mapped_column(server_default="0")
    status: Mapped[BillStatus] = mapped_column(
        _enum(BillStatus, "bill_status"), server_default=BillStatus.OPEN.value
    )
    created_at: Mapped[dt.datetime] = _created_at()


class BillReminder(Base):
    """See planning/03-tech-stack.md#6-scheduling."""

    __tablename__ = "bill_reminders"
    __table_args__ = (UniqueConstraint("bill_id", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"))
    kind: Mapped[str] = mapped_column(String(32))
    sent_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"), index=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"))
    amount: Mapped[Decimal]
    paid_on: Mapped[dt.date]
    created_at: Mapped[dt.datetime] = _created_at()


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("cost > 0", name="cost_positive"),
        CheckConstraint("salvage >= 0 AND salvage <= cost", name="salvage_range"),
        CheckConstraint("life_months > 0", name="life_months_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    purchase_date: Mapped[dt.date]
    cost: Mapped[Decimal]
    salvage: Mapped[Decimal] = mapped_column(server_default="0")
    life_months: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(32), server_default="straight_line")
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    created_at: Mapped[dt.datetime] = _created_at()


class TelegramUpdate(Base):
    __tablename__ = "telegram_updates"

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    received_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    processed_at: Mapped[dt.datetime | None]


class ScheduledRun(Base):
    __tablename__ = "scheduled_runs"
    __table_args__ = (UniqueConstraint("job", "slot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job: Mapped[str] = mapped_column(String(64))
    slot: Mapped[str] = mapped_column(String(64))
    ran_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_ref", "ref_type", "ref_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), index=True)
    actor: Mapped[AuditActor] = mapped_column(_enum(AuditActor, "audit_actor"))
    action: Mapped[str] = mapped_column(String(64))
    ref_type: Mapped[str | None] = mapped_column(String(32))
    ref_id: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(64))
    detail_json: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    thread_id: Mapped[str] = mapped_column(String(128), unique=True)
    checkpoint_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[dt.datetime] = _created_at()
    updated_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class WebSession(Base):
    """See planning/03-tech-stack.md section 3.2 (itsdangerous row)."""

    __tablename__ = "web_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[dt.datetime] = _created_at()
    expires_at: Mapped[dt.datetime] = mapped_column(index=True)
    last_seen_at: Mapped[dt.datetime | None]
    revoked_at: Mapped[dt.datetime | None]
