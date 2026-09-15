"""add_relative_leadership_exit_reason

Revision ID: f6a2e1c9d5b8
Revises: bcbcbce99169
Create Date: 2026-09-15

Adds RELATIVE_LEADERSHIP_DETERIORATION to the exitreason enum for the relative_leadership_v1
strategy's 3-session deterioration exit. Additive only — downgrade is a no-op since Postgres
can't drop enum values without rebuilding the type (irrelevant here: nothing gets backed
into the old values).
"""
from alembic import op

revision = 'f6a2e1c9d5b8'
down_revision = 'bcbcbce99169'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside the same transaction as a statement that
    # might use the new value, so this needs to commit on its own.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE exitreason ADD VALUE IF NOT EXISTS 'relative_leadership_deterioration'")


def downgrade() -> None:
    # Postgres has no direct "remove enum value" — would require rebuilding the type and
    # every dependent column/constraint. No rows use this value outside this migration's
    # own upgrade path, so left as a no-op rather than a destructive type rebuild.
    pass
