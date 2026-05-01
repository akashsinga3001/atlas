"""Add ML backtesting schema tables.

Revision ID: 20260501_backtest_wf
Revises: c2a9d7b1e6f4
Create Date: 2026-05-01 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '20260501_backtest_wf'
down_revision = 'c2a9d7b1e6f4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create/update backtest schema tables for ML walk-forward validation."""
    
    # Drop old backtest schema tables if they exist (from previous migration)
    op.execute('DROP TABLE IF EXISTS backtest_trades CASCADE')
    op.execute('DROP TABLE IF EXISTS backtest_runs CASCADE')
    
    # Create backtest_runs table
    op.create_table(
        'backtest_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_name', sa.String(128), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='completed'),
        sa.Column('train_start_date', sa.Date(), nullable=False),
        sa.Column('train_end_date', sa.Date(), nullable=False),
        sa.Column('test_start_date', sa.Date(), nullable=False),
        sa.Column('test_end_date', sa.Date(), nullable=False),
        sa.Column('strategy_version', sa.String(64), nullable=False),
        sa.Column('use_enhanced_features', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('use_ensemble', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('total_folds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('train_window_days', sa.Integer(), nullable=False),
        sa.Column('test_window_days', sa.Integer(), nullable=False),
        sa.Column('total_predictions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_trades_simulated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('winning_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('losing_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('win_rate_pct', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('accuracy_pct', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('precision_at_5', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('precision_at_10', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('total_return_pct', sa.Numeric(12, 4), nullable=False, server_default='0'),
        sa.Column('sharpe_ratio', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('max_drawdown_pct', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('avg_trade_return_pct', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('long_accuracy_pct', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('short_accuracy_pct', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('fold_metrics', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('model_comparison', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('backtest_name', name='uq_backtest_runs_backtest_name'),
    )
    op.create_index('ix_backtest_runs_status_created_at', 'backtest_runs', ['status', 'created_at'])
    op.create_index('ix_backtest_runs_test_date_range', 'backtest_runs', ['test_start_date', 'test_end_date'])

    # Create backtest_positions table
    op.create_table(
        'backtest_positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_run_id', sa.Integer(), nullable=False),
        sa.Column('security_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(32), nullable=False),
        sa.Column('direction', sa.String(8), nullable=False),
        sa.Column('confidence', sa.Numeric(10, 6), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('entry_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('position_size', sa.Numeric(18, 2), nullable=False),
        sa.Column('stop_loss_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('take_profit_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('exit_date', sa.Date(), nullable=True),
        sa.Column('exit_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('exit_reason', sa.String(32), nullable=True),
        sa.Column('target_move_pct', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('actual_move_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('hit', sa.Boolean(), nullable=True),
        sa.Column('realized_pnl', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('realized_pnl_pct', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('days_held', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['security_id'], ['securities.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_backtest_positions_backtest_run_id', 'backtest_positions', ['backtest_run_id'])
    op.create_index('ix_backtest_positions_security_date', 'backtest_positions', ['security_id', 'entry_date'])
    op.create_index('ix_backtest_positions_pnl', 'backtest_positions', ['realized_pnl_pct'])

    # Create backtest_predictions table
    op.create_table(
        'backtest_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_run_id', sa.Integer(), nullable=False),
        sa.Column('security_id', sa.Integer(), nullable=False),
        sa.Column('prediction_date', sa.Date(), nullable=False),
        sa.Column('ticker', sa.String(32), nullable=False),
        sa.Column('direction', sa.String(8), nullable=False),
        sa.Column('predicted_confidence', sa.Numeric(10, 6), nullable=False),
        sa.Column('predicted_rank', sa.Integer(), nullable=True),
        sa.Column('horizon_days', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('threshold_pct', sa.Numeric(10, 4), nullable=False, server_default='5.0'),
        sa.Column('actual_move_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('hit', sa.Boolean(), nullable=True),
        sa.Column('entry_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('exit_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('pnl_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('top_features', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('backtest_run_id', 'prediction_date', 'security_id', 'direction', name='uq_backtest_pred_date_sec_dir'),
        sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['security_id'], ['securities.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_backtest_predictions_backtest_run_id', 'backtest_predictions', ['backtest_run_id'])
    op.create_index('ix_backtest_predictions_date_direction', 'backtest_predictions', ['prediction_date', 'direction'])
    op.create_index('ix_backtest_predictions_hit', 'backtest_predictions', ['hit'])

    # Create backtest_daily_metrics table
    op.create_table(
        'backtest_daily_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_run_id', sa.Integer(), nullable=False),
        sa.Column('metric_date', sa.Date(), nullable=False),
        sa.Column('portfolio_value', sa.Numeric(18, 2), nullable=False),
        sa.Column('cumulative_return_pct', sa.Numeric(12, 4), nullable=False),
        sa.Column('daily_return_pct', sa.Numeric(10, 4), nullable=False),
        sa.Column('max_drawdown_to_date_pct', sa.Numeric(10, 4), nullable=False),
        sa.Column('open_positions_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('closed_positions_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('trades_won_today', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('trades_lost_today', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('backtest_run_id', 'metric_date', name='uq_backtest_daily_date'),
        sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_backtest_daily_backtest_run_id', 'backtest_daily_metrics', ['backtest_run_id'])

    # Create backtest_ensemble_training table
    op.create_table(
        'backtest_ensemble_training',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_run_id', sa.Integer(), nullable=False),
        sa.Column('fold_number', sa.Integer(), nullable=False),
        sa.Column('fold_name', sa.String(64), nullable=False),
        sa.Column('train_start_date', sa.Date(), nullable=False),
        sa.Column('train_end_date', sa.Date(), nullable=False),
        sa.Column('test_start_date', sa.Date(), nullable=False),
        sa.Column('test_end_date', sa.Date(), nullable=False),
        sa.Column('train_samples', sa.Integer(), nullable=False),
        sa.Column('test_samples', sa.Integer(), nullable=False),
        sa.Column('rf_model_path', sa.String(512), nullable=True),
        sa.Column('lgb_model_path', sa.String(512), nullable=True),
        sa.Column('xgb_model_path', sa.String(512), nullable=True),
        sa.Column('rf_accuracy', sa.Numeric(10, 4), nullable=True),
        sa.Column('rf_precision_at_5', sa.Numeric(10, 4), nullable=True),
        sa.Column('rf_sharpe', sa.Numeric(10, 4), nullable=True),
        sa.Column('lgb_accuracy', sa.Numeric(10, 4), nullable=True),
        sa.Column('lgb_precision_at_5', sa.Numeric(10, 4), nullable=True),
        sa.Column('lgb_sharpe', sa.Numeric(10, 4), nullable=True),
        sa.Column('xgb_accuracy', sa.Numeric(10, 4), nullable=True),
        sa.Column('xgb_precision_at_5', sa.Numeric(10, 4), nullable=True),
        sa.Column('xgb_sharpe', sa.Numeric(10, 4), nullable=True),
        sa.Column('ensemble_accuracy', sa.Numeric(10, 4), nullable=False),
        sa.Column('ensemble_precision_at_5', sa.Numeric(10, 4), nullable=False),
        sa.Column('ensemble_sharpe', sa.Numeric(10, 4), nullable=False),
        sa.Column('long_accuracy', sa.Numeric(10, 4), nullable=False),
        sa.Column('short_accuracy', sa.Numeric(10, 4), nullable=False),
        sa.Column('model_comparison', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('backtest_run_id', 'fold_number', name='uq_backtest_ensemble_fold'),
        sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_backtest_ensemble_backtest_run_id', 'backtest_ensemble_training', ['backtest_run_id'])


def downgrade() -> None:
    """Drop backtest schema tables."""
    op.drop_index('ix_backtest_ensemble_backtest_run_id', table_name='backtest_ensemble_training')
    op.drop_table('backtest_ensemble_training')
    op.drop_index('ix_backtest_daily_backtest_run_id', table_name='backtest_daily_metrics')
    op.drop_table('backtest_daily_metrics')
    op.drop_index('ix_backtest_predictions_hit', table_name='backtest_predictions')
    op.drop_index('ix_backtest_predictions_date_direction', table_name='backtest_predictions')
    op.drop_index('ix_backtest_predictions_backtest_run_id', table_name='backtest_predictions')
    op.drop_table('backtest_predictions')
    op.drop_index('ix_backtest_positions_pnl', table_name='backtest_positions')
    op.drop_index('ix_backtest_positions_security_date', table_name='backtest_positions')
    op.drop_index('ix_backtest_positions_backtest_run_id', table_name='backtest_positions')
    op.drop_table('backtest_positions')
    op.drop_index('ix_backtest_runs_test_date_range', table_name='backtest_runs')
    op.drop_index('ix_backtest_runs_status_created_at', table_name='backtest_runs')
    op.drop_table('backtest_runs')
