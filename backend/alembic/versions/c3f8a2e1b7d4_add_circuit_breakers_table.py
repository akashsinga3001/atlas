"""add_circuit_breakers_table

Revision ID: c3f8a2e1b7d4
Revises: 85e61d3c34c9
Create Date: 2026-08-15

"""
import sqlalchemy as sa
from alembic import op

revision = 'c3f8a2e1b7d4'
down_revision = '85e61d3c34c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "circuit_breakers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("type", sa.String(length=50), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reason", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    table = sa.table("circuit_breakers", sa.column("type", sa.String), sa.column("enabled", sa.Boolean), sa.column("params", sa.JSON))
    op.bulk_insert(table, [{ "type": "drawdown", "enabled": True, "params": { "threshold_pct": 5.0 } }])


def downgrade() -> None:
    op.drop_table("circuit_breakers")
