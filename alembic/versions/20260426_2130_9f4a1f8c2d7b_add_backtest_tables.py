"""add_backtest_tables

Revision ID: 9f4a1f8c2d7b
Revises: 1b2f7f50a9f3
Create Date: 2026-04-26 21:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f4a1f8c2d7b'
down_revision = '1b2f7f50a9f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'backtest_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('strategy_name', sa.String(length=64), nullable=False),
        sa.Column('strategy_params', sa.JSON(), nullable=False),
        sa.Column('timeframe', sa.String(length=16), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('allow_short', sa.Boolean(), nullable=False),
        sa.Column('transaction_cost_bps', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('slippage_bps', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('initial_capital', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('final_capital', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('total_return_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('max_drawdown_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=False),
        sa.Column('win_rate_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('avg_trade_return_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('notes', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_backtest_runs_strategy_created_at', 'backtest_runs', ['strategy_name', 'created_at'], unique=False)
    op.create_index('ix_backtest_runs_timeframe_created_at', 'backtest_runs', ['timeframe', 'created_at'], unique=False)

    op.create_table(
        'backtest_trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('backtest_run_id', sa.Integer(), nullable=False),
        sa.Column('security_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=32), nullable=False),
        sa.Column('direction', sa.String(length=8), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('exit_date', sa.Date(), nullable=False),
        sa.Column('entry_price', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('exit_price', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('entry_signal', sa.String(length=32), nullable=False),
        sa.Column('exit_signal', sa.String(length=32), nullable=False),
        sa.Column('gross_pnl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('net_pnl', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('return_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('bars_held', sa.Integer(), nullable=False),
        sa.Column('entry_features', sa.JSON(), nullable=True),
        sa.Column('exit_features', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['security_id'], ['securities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_backtest_trades_backtest_run_id', 'backtest_trades', ['backtest_run_id'], unique=False)
    op.create_index('ix_backtest_trades_security_id', 'backtest_trades', ['security_id'], unique=False)
    op.create_index('ix_backtest_trades_run_security', 'backtest_trades', ['backtest_run_id', 'security_id'], unique=False)
    op.create_index('ix_backtest_trades_direction_exit_date', 'backtest_trades', ['direction', 'exit_date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_backtest_trades_direction_exit_date', table_name='backtest_trades')
    op.drop_index('ix_backtest_trades_run_security', table_name='backtest_trades')
    op.drop_index('ix_backtest_trades_security_id', table_name='backtest_trades')
    op.drop_index('ix_backtest_trades_backtest_run_id', table_name='backtest_trades')
    op.drop_table('backtest_trades')

    op.drop_index('ix_backtest_runs_timeframe_created_at', table_name='backtest_runs')
    op.drop_index('ix_backtest_runs_strategy_created_at', table_name='backtest_runs')
    op.drop_table('backtest_runs')
