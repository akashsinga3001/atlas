"""add_kill_switch_table

Revision ID: 85e61d3c34c9
Revises: 01e72a75850f
Create Date: 2026-08-15

"""
import sqlalchemy as sa
from alembic import op

revision = '85e61d3c34c9'
down_revision = '01e72a75850f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kill_switch",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    table = sa.table("kill_switch", sa.column("id", sa.BigInteger), sa.column("enabled", sa.Boolean))
    op.bulk_insert(table, [{ "id": 1, "enabled": False }])


def downgrade() -> None:
    op.drop_table("kill_switch")
