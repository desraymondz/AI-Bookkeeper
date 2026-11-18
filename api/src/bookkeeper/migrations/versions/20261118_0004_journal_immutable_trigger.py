"""Refuse UPDATE and DELETE on posted journal entries and lines. See planning/decisions.md#D-035.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18 00:00:00+00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FUNCTION = """
CREATE OR REPLACE FUNCTION journal_immutable() RETURNS trigger AS $$
DECLARE
    parent_status text;
BEGIN
    IF TG_TABLE_NAME = 'journal_entries' THEN
        IF OLD.status = 'posted' THEN
            RAISE EXCEPTION 'journal entry % is posted and cannot be changed', OLD.id
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    ELSE
        SELECT status INTO parent_status FROM journal_entries WHERE id = OLD.entry_id;
        IF parent_status = 'posted' THEN
            RAISE EXCEPTION 'lines of posted journal entry % cannot be changed', OLD.entry_id
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.execute(_FUNCTION)
    op.execute(
        "CREATE TRIGGER journal_entries_immutable BEFORE UPDATE OR DELETE ON journal_entries "
        "FOR EACH ROW EXECUTE FUNCTION journal_immutable()"
    )
    op.execute(
        "CREATE TRIGGER journal_lines_immutable BEFORE UPDATE OR DELETE ON journal_lines "
        "FOR EACH ROW EXECUTE FUNCTION journal_immutable()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS journal_lines_immutable ON journal_lines")
    op.execute("DROP TRIGGER IF EXISTS journal_entries_immutable ON journal_entries")
    op.execute("DROP FUNCTION IF EXISTS journal_immutable()")
