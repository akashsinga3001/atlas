"""add_created_at_to_strategy_versions

Revision ID: 2e295b61e2e7
Revises: f7a3c1e9b4d2
Create Date: 2026-08-15

"""
import sqlalchemy as sa
from alembic import op

revision = '2e295b61e2e7'
down_revision = 'f7a3c1e9b4d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("strategy_versions", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_column("strategy_versions", "created_at")
