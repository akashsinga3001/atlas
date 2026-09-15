"""add_cancelled_trade_status

Revision ID: a3d7e0f21c4a
Revises: f6a2e1c9d5b8
Create Date: 2026-09-15

Adds CANCELLED to the tradestatus enum. A PENDING entry order that Kite ultimately rejects,
cancels, or lets expire unfilled (day order, no fill by market close) previously had no
terminal state to move to — it stayed PENDING forever, permanently consuming a strategy's
trade slot. Additive only — downgrade is a no-op since Postgres can't drop enum values
without rebuilding the type.
"""
from alembic import op

revision = 'a3d7e0f21c4a'
down_revision = 'f6a2e1c9d5b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside the same transaction as a statement that
    # might use the new value, so this needs to commit on its own.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE tradestatus ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    # Postgres has no direct "remove enum value" — would require rebuilding the type and
    # every dependent column/constraint. No rows use this value outside this migration's
    # own upgrade path, so left as a no-op rather than a destructive type rebuild.
    pass
