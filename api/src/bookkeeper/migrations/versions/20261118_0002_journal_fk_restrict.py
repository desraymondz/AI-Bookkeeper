"""Journal line and check result FKs to RESTRICT. See planning/decisions.md#D-018.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-18 00:00:00+00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FKS = (
    ("journal_lines", "fk_journal_lines_entry_id_journal_entries"),
    ("check_results", "fk_check_results_entry_id_journal_entries"),
)


def _recreate(ondelete: str) -> None:
    for table, name in _FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(
            name, table, "journal_entries", ["entry_id"], ["id"], ondelete=ondelete
        )


def upgrade() -> None:
    _recreate("RESTRICT")


def downgrade() -> None:
    _recreate("CASCADE")
