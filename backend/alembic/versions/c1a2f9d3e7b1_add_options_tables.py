"""add_options_tables

Revision ID: c1a2f9d3e7b1
Revises: add_fund_tables
Create Date: 2026-08-14

"""
from alembic import op
import sqlalchemy as sa


revision = 'c1a2f9d3e7b1'
down_revision = 'add_fund_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('securities', sa.Column('strike', sa.Numeric(precision=12, scale=4), nullable=True))
    op.add_column('securities', sa.Column('option_type', sa.String(length=2), nullable=True))

    op.create_table(
        'options_positions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('strategy_signal_id', sa.BigInteger(), nullable=False),
        sa.Column('strategy_version_id', sa.BigInteger(), nullable=False),
        sa.Column('signal_date', sa.Date(), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('spot_at_signal', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('call_short_strike', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('put_short_strike', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('call_long_strike', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('put_long_strike', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('lots', sa.Integer(), nullable=True),
        sa.Column('lot_size', sa.Integer(), nullable=True),
        sa.Column('margin_per_lot', sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column('net_credit_per_lot', sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column('status', sa.Enum('pending', 'open', 'closing', 'closed', 'failed', 'skipped', name='optionspositionstatus'), nullable=False),
        sa.Column('skip_reason', sa.String(length=255), nullable=True),
        sa.Column('planned_exit_date', sa.Date(), nullable=True),
        sa.Column('exit_date', sa.Date(), nullable=True),
        sa.Column('exit_reason', sa.Enum('time_exit', 'expiry_exit', name='optionsexitreason'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['strategy_signal_id'], ['strategy_signals.id'], ),
        sa.ForeignKeyConstraint(['strategy_version_id'], ['strategy_versions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('strategy_signal_id', name='uix_options_position_signal'),
    )
    op.create_index(op.f('ix_options_positions_strategy_signal_id'), 'options_positions', ['strategy_signal_id'], unique=True)
    op.create_index(op.f('ix_options_positions_strategy_version_id'), 'options_positions', ['strategy_version_id'], unique=False)

    op.create_table(
        'options_legs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('options_position_id', sa.BigInteger(), nullable=False),
        sa.Column('security_id', sa.BigInteger(), nullable=False),
        sa.Column('role', sa.Enum('short_call', 'short_put', 'long_call', 'long_put', name='optionslegrole'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'open', 'closed', 'failed', name='optionslegstatus'), nullable=False),
        sa.Column('kite_entry_order_id', sa.String(length=100), nullable=True),
        sa.Column('entry_fill_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('entry_fill_quantity', sa.Integer(), nullable=True),
        sa.Column('entry_date', sa.Date(), nullable=True),
        sa.Column('kite_exit_order_id', sa.String(length=100), nullable=True),
        sa.Column('exit_fill_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('exit_fill_quantity', sa.Integer(), nullable=True),
        sa.Column('exit_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['options_position_id'], ['options_positions.id'], ),
        sa.ForeignKeyConstraint(['security_id'], ['securities.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('options_position_id', 'role', name='uix_options_leg_position_role'),
    )
    op.create_index(op.f('ix_options_legs_options_position_id'), 'options_legs', ['options_position_id'], unique=False)
    op.create_index(op.f('ix_options_legs_security_id'), 'options_legs', ['security_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_options_legs_security_id'), table_name='options_legs')
    op.drop_index(op.f('ix_options_legs_options_position_id'), table_name='options_legs')
    op.drop_table('options_legs')

    op.drop_index(op.f('ix_options_positions_strategy_version_id'), table_name='options_positions')
    op.drop_index(op.f('ix_options_positions_strategy_signal_id'), table_name='options_positions')
    op.drop_table('options_positions')

    op.execute('DROP TYPE IF EXISTS optionslegstatus')
    op.execute('DROP TYPE IF EXISTS optionslegrole')
    op.execute('DROP TYPE IF EXISTS optionsexitreason')
    op.execute('DROP TYPE IF EXISTS optionspositionstatus')

    op.drop_column('securities', 'option_type')
    op.drop_column('securities', 'strike')
