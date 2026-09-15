"""add_mom_6_1_to_security_features

Revision ID: bcbcbce99169
Revises: e91a4c7d2f68
Create Date: 2026-09-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'bcbcbce99169'
down_revision = 'e91a4c7d2f68'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('security_features', sa.Column('mom_6_1', sa.Numeric(precision=18, scale=8), nullable=True))


def downgrade() -> None:
    op.drop_column('security_features', 'mom_6_1')
