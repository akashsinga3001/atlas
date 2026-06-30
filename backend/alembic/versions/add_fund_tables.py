"""add_fund_tables

Revision ID: add_fund_tables
Revises: 3b0f113934d9
Create Date: 2026-06-30

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_fund_tables'
down_revision = '3b0f113934d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('cash_flows', sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False), sa.Column('flow_type', sa.Enum('deposit', 'withdrawal', name='flowtype'), nullable=False), sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False), sa.Column('flow_date', sa.Date(), nullable=False), sa.Column('note', sa.String(length=255), nullable=True), sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False), sa.PrimaryKeyConstraint('id'), )
    op.create_index(op.f('ix_cash_flows_flow_date'), 'cash_flows', ['flow_date'], unique=False)

    op.create_table(
        'account_snapshots', sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False), sa.Column('snapshot_date', sa.Date(), nullable=False), sa.Column('cash_balance', sa.Numeric(precision=14, scale=2), nullable=False), sa.Column('holdings_value', sa.Numeric(precision=14, scale=2), nullable=False), sa.Column('total_value', sa.Numeric(precision=14, scale=2), nullable=False), sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'), sa.UniqueConstraint('snapshot_date', name='uix_account_snapshot_date'),
    )
    op.create_index(op.f('ix_account_snapshots_snapshot_date'), 'account_snapshots', ['snapshot_date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_account_snapshots_snapshot_date'), table_name='account_snapshots')
    op.drop_table('account_snapshots')
    op.drop_index(op.f('ix_cash_flows_flow_date'), table_name='cash_flows')
    op.drop_table('cash_flows')
    op.execute('DROP TYPE IF EXISTS flowtype')
