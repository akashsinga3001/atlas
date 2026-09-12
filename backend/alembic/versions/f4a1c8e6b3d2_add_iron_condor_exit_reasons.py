"""add_iron_condor_exit_reasons

Revision ID: f4a1c8e6b3d2
Revises: e91a4c7d2f68
Create Date: 2026-09-10

Adds PROFIT_TARGET/STOP_LOSS/CREDIT_RECONCILIATION to the optionsexitreason enum for the
delta-targeted NIFTY iron condor's exit logic (profit-target/stop-loss/credit-reconciliation
exits alongside the existing TIME_EXIT/EXPIRY_EXIT). Additive only — no existing rows use
these values, and downgrade is a no-op since Postgres can't drop enum values without
rebuilding the type (irrelevant here: nothing gets backed into the old two values).
"""
from alembic import op

revision = 'f4a1c8e6b3d2'
down_revision = 'e91a4c7d2f68'
branch_labels = None
depends_on = None

NEW_VALUES = ('profit_target', 'stop_loss', 'credit_reconciliation')


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside the same transaction as a statement that
    # might use the new value, so this needs to commit on its own.
    with op.get_context().autocommit_block():
        for value in NEW_VALUES:
            op.execute(f"ALTER TYPE optionsexitreason ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres has no direct "remove enum value" — would require rebuilding the type and
    # every dependent column/constraint. No rows use these values outside this migration's
    # own upgrade path, so left as a no-op rather than a destructive type rebuild.
    pass
