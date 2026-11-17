"""Accounts Payable subtype to trade_payable. See planning/decisions.md#D-030.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-18 00:00:00+00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE accounts SET subtype = 'trade_payable' "
        "WHERE code = '2000' AND type = 'liability' AND subtype = 'current_liability'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE accounts SET subtype = 'current_liability' "
        "WHERE code = '2000' AND type = 'liability' AND subtype = 'trade_payable'"
    )
