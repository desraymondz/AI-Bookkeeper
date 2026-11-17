"""Initial schema: every table in planning/01-prd.md#data-model-sketch plus web_sessions.

Revision ID: 0001
Revises:
Create Date: 2026-11-17 17:09:57.700060+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "asset",
                "liability",
                "equity",
                "revenue",
                "expense",
                "contra_asset",
                name="account_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("subtype", sa.String(length=32), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
        sa.UniqueConstraint("code", name=op.f("uq_accounts_code")),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "actor",
            sa.Enum(
                "agent",
                "boss",
                "system",
                name="audit_actor",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("ref_type", sa.String(length=32), nullable=True),
        sa.Column("ref_id", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column(
            "detail_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(op.f("ix_audit_log_at"), "audit_log", ["at"], unique=False)
    op.create_index("ix_audit_log_ref", "audit_log", ["ref_type", "ref_id"], unique=False)
    op.create_table(
        "business_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="SGD", nullable=False),
        sa.Column(
            "timezone", sa.String(length=64), server_default="Asia/Singapore", nullable=False
        ),
        sa.Column("fy_start_month", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("gst_registered", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "gst_rate", sa.Numeric(precision=5, scale=2), server_default="9.00", nullable=False
        ),
        sa.Column("price_rule", sa.String(length=32), server_default="any_change", nullable=False),
        sa.Column("dup_window_days", sa.Integer(), server_default="180", nullable=False),
        sa.Column("reminder_days", sa.Integer(), server_default="3", nullable=False),
        sa.Column("recap_time", sa.Time(), server_default="21:00", nullable=False),
        sa.Column("report_day", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("report_time", sa.Time(), server_default="09:00", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "dup_window_days >= 0", name=op.f("ck_business_settings_dup_window_days_nonneg")
        ),
        sa.CheckConstraint(
            "fy_start_month BETWEEN 1 AND 12",
            name=op.f("ck_business_settings_fy_start_month_range"),
        ),
        sa.CheckConstraint(
            "gst_rate >= 0 AND gst_rate <= 100", name=op.f("ck_business_settings_gst_rate_range")
        ),
        sa.CheckConstraint(
            "reminder_days >= 0", name=op.f("ck_business_settings_reminder_days_nonneg")
        ),
        sa.CheckConstraint(
            "report_day BETWEEN 1 AND 28", name=op.f("ck_business_settings_report_day_range")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_settings")),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("checkpoint_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
        sa.UniqueConstraint("thread_id", name=op.f("uq_conversations_thread_id")),
    )
    op.create_index(
        op.f("ix_conversations_telegram_user_id"),
        "conversations",
        ["telegram_user_id"],
        unique=False,
    )
    op.create_table(
        "periods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("month", sa.SmallInteger(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "closing",
                "locked",
                name="period_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="open",
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("month BETWEEN 1 AND 12", name=op.f("ck_periods_month_range")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_periods")),
        sa.UniqueConstraint("year", "month", name=op.f("uq_periods_year_month")),
    )
    op.create_table(
        "scheduled_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job", sa.String(length=64), nullable=False),
        sa.Column("slot", sa.String(length=64), nullable=False),
        sa.Column(
            "ran_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheduled_runs")),
        sa.UniqueConstraint("job", "slot", name=op.f("uq_scheduled_runs_job_slot")),
    )
    op.create_table(
        "strangers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("first_message_preview", sa.Text(), nullable=True),
        sa.Column(
            "first_seen",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "decision",
            sa.Enum(
                "pending",
                "ignored",
                "blocked",
                "added",
                name="stranger_decision",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strangers")),
        sa.UniqueConstraint("telegram_user_id", name=op.f("uq_strangers_telegram_user_id")),
    )
    op.create_table(
        "telegram_updates",
        sa.Column("update_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("update_id", name=op.f("pk_telegram_updates")),
    )
    op.create_table(
        "web_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_web_sessions")),
    )
    op.create_index(
        op.f("ix_web_sessions_expires_at"), "web_sessions", ["expires_at"], unique=False
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("cost", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("salvage", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False),
        sa.Column("life_months", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=32), server_default="straight_line", nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("cost > 0", name=op.f("ck_assets_cost_positive")),
        sa.CheckConstraint("life_months > 0", name=op.f("ck_assets_life_months_positive")),
        sa.CheckConstraint(
            "salvage >= 0 AND salvage <= cost", name=op.f("ck_assets_salvage_range")
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], name=op.f("fk_assets_account_id_accounts")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assets")),
    )
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("uen", sa.String(length=32), nullable=True),
        sa.Column("default_account_id", sa.Integer(), nullable=False),
        sa.Column("terms_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("telegram_username_hint", sa.String(length=64), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("terms_days >= 0", name=op.f("ck_suppliers_terms_days_nonneg")),
        sa.ForeignKeyConstraint(
            ["default_account_id"],
            ["accounts.id"],
            name=op.f("fk_suppliers_default_account_id_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suppliers")),
    )
    op.create_table(
        "link_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum(
                "boss",
                "supplier",
                name="link_purpose",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by_telegram_user_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(purpose = 'supplier') = (supplier_id IS NOT NULL)",
            name=op.f("ck_link_tokens_supplier_link_matches_purpose"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], name=op.f("fk_link_tokens_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_link_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_link_tokens_token_hash")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "boss",
                "supplier",
                name="user_role",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "deactivated",
                "blocked",
                name="user_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(role = 'supplier') = (supplier_id IS NOT NULL)",
            name=op.f("ck_users_supplier_link_matches_role"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], name=op.f("fk_users_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("telegram_user_id", name=op.f("uq_users_telegram_user_id")),
    )
    op.create_index(
        "uq_users_one_active_boss",
        "users",
        ["role"],
        unique=True,
        postgresql_where=sa.text("role = 'boss' AND status = 'active'"),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("preview_path", sa.Text(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("mime", sa.String(length=128), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "kind",
            sa.Enum(
                "invoice",
                "sales",
                "excel",
                name="document_kind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.CheckConstraint("size >= 0", name=op.f("ck_documents_size_nonneg")),
        sa.ForeignKeyConstraint(
            ["sender_user_id"], ["users.id"], name=op.f("fk_documents_sender_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("sha256", name=op.f("uq_documents_sha256")),
    )
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("invoice_no", sa.String(length=64), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("gst", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column(
            "extraction_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name=op.f("fk_invoices_document_id_documents")
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], name=op.f("fk_invoices_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoices")),
    )
    op.create_index(op.f("ix_invoices_document_id"), "invoices", ["document_id"], unique=False)
    op.create_index(op.f("ix_invoices_supplier_id"), "invoices", ["supplier_id"], unique=False)
    op.create_table(
        "bills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "paid_amount", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False
        ),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "paid",
                name="bill_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="open",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_bills_amount_positive")),
        sa.CheckConstraint(
            "paid_amount >= 0 AND paid_amount <= amount", name=op.f("ck_bills_paid_amount_range")
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.id"], name=op.f("fk_bills_invoice_id_invoices")
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], name=op.f("fk_bills_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bills")),
        sa.UniqueConstraint("invoice_id", name=op.f("uq_bills_invoice_id")),
    )
    op.create_index(op.f("ix_bills_supplier_id"), "bills", ["supplier_id"], unique=False)
    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("normalized_item", sa.String(length=200), nullable=True),
        sa.Column("qty", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("line_total", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name=op.f("fk_invoice_lines_invoice_id_invoices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoice_lines")),
    )
    op.create_index(
        op.f("ix_invoice_lines_invoice_id"), "invoice_lines", ["invoice_id"], unique=False
    )
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_no", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "auto",
                "boss_approved",
                "manual",
                "system",
                name="entry_source",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "proposed",
                "pending_approval",
                "posted",
                "rejected",
                name="entry_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="proposed",
            nullable=False,
        ),
        sa.Column(
            "kind",
            sa.Enum(
                "normal",
                "adjusting",
                "opening",
                "reversal",
                "closing",
                name="entry_kind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="normal",
            nullable=False,
        ),
        sa.Column("reverses_id", sa.Integer(), nullable=True),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("period_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.id"], name=op.f("fk_journal_entries_invoice_id_invoices")
        ),
        sa.ForeignKeyConstraint(
            ["period_id"], ["periods.id"], name=op.f("fk_journal_entries_period_id_periods")
        ),
        sa.ForeignKeyConstraint(
            ["reverses_id"],
            ["journal_entries.id"],
            name=op.f("fk_journal_entries_reverses_id_journal_entries"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_entries")),
        sa.UniqueConstraint("entry_no", name=op.f("uq_journal_entries_entry_no")),
    )
    op.create_index(op.f("ix_journal_entries_date"), "journal_entries", ["date"], unique=False)
    op.create_index(
        op.f("ix_journal_entries_invoice_id"), "journal_entries", ["invoice_id"], unique=False
    )
    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "decision",
            sa.Enum(
                "approve",
                "edit",
                "reject",
                "ignore_duplicate",
                "post_anyway",
                name="approval_decision",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["journal_entries.id"], name=op.f("fk_approvals_entry_id_journal_entries")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approvals")),
    )
    op.create_index(op.f("ix_approvals_entry_id"), "approvals", ["entry_id"], unique=False)
    op.create_table(
        "bill_reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column(
            "sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["bill_id"], ["bills.id"], name=op.f("fk_bill_reminders_bill_id_bills")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bill_reminders")),
        sa.UniqueConstraint("bill_id", "kind", name=op.f("uq_bill_reminders_bill_id_kind")),
    )
    op.create_table(
        "check_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("check_code", sa.String(length=32), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["journal_entries.id"],
            name=op.f("fk_check_results_entry_id_journal_entries"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_check_results")),
    )
    op.create_index(op.f("ix_check_results_entry_id"), "check_results", ["entry_id"], unique=False)
    op.create_table(
        "journal_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("debit", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False),
        sa.Column("credit", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
            name=op.f("ck_journal_lines_one_side_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], name=op.f("fk_journal_lines_account_id_accounts")
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["journal_entries.id"],
            name=op.f("fk_journal_lines_entry_id_journal_entries"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_lines")),
    )
    op.create_index(
        op.f("ix_journal_lines_account_id"), "journal_lines", ["account_id"], unique=False
    )
    op.create_index(op.f("ix_journal_lines_entry_id"), "journal_lines", ["entry_id"], unique=False)
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_payments_amount_positive")),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"], name=op.f("fk_payments_bill_id_bills")),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["journal_entries.id"], name=op.f("fk_payments_entry_id_journal_entries")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
    )
    op.create_index(op.f("ix_payments_bill_id"), "payments", ["bill_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_bill_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_journal_lines_entry_id"), table_name="journal_lines")
    op.drop_index(op.f("ix_journal_lines_account_id"), table_name="journal_lines")
    op.drop_table("journal_lines")
    op.drop_index(op.f("ix_check_results_entry_id"), table_name="check_results")
    op.drop_table("check_results")
    op.drop_table("bill_reminders")
    op.drop_index(op.f("ix_approvals_entry_id"), table_name="approvals")
    op.drop_table("approvals")
    op.drop_index(op.f("ix_journal_entries_invoice_id"), table_name="journal_entries")
    op.drop_index(op.f("ix_journal_entries_date"), table_name="journal_entries")
    op.drop_table("journal_entries")
    op.drop_index(op.f("ix_invoice_lines_invoice_id"), table_name="invoice_lines")
    op.drop_table("invoice_lines")
    op.drop_index(op.f("ix_bills_supplier_id"), table_name="bills")
    op.drop_table("bills")
    op.drop_index(op.f("ix_invoices_supplier_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_document_id"), table_name="invoices")
    op.drop_table("invoices")
    op.drop_table("documents")
    op.drop_index(
        "uq_users_one_active_boss",
        table_name="users",
        postgresql_where=sa.text("role = 'boss' AND status = 'active'"),
    )
    op.drop_table("users")
    op.drop_table("link_tokens")
    op.drop_table("suppliers")
    op.drop_table("assets")
    op.drop_index(op.f("ix_web_sessions_expires_at"), table_name="web_sessions")
    op.drop_table("web_sessions")
    op.drop_table("telegram_updates")
    op.drop_table("strangers")
    op.drop_table("scheduled_runs")
    op.drop_table("periods")
    op.drop_index(op.f("ix_conversations_telegram_user_id"), table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("business_settings")
    op.drop_index("ix_audit_log_ref", table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_at"), table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("accounts")
    op.execute("DROP EXTENSION IF EXISTS vector")
