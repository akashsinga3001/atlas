"""Persistent models for ML backtesting, walk-forward validation, and performance tracking."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class BacktestRun(Base):
    """Stores metadata and aggregate metrics for one walk-forward backtest execution."""

    __tablename__ = 'backtest_runs'
    __table_args__ = (
        UniqueConstraint('backtest_name', name='uq_backtest_runs_backtest_name'),
        Index('ix_backtest_runs_status_created_at', 'status', 'created_at'),
        Index('ix_backtest_runs_test_date_range', 'test_start_date', 'test_end_date'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backtest_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='completed')  # 'running', 'completed', 'failed'

    train_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    train_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    test_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    test_end_date: Mapped[date] = mapped_column(Date, nullable=False)

    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g., 'ensemble_rf_lgb_xgb_v1'
    use_enhanced_features: Mapped[bool] = mapped_column(default=False)
    use_ensemble: Mapped[bool] = mapped_column(default=False)

    total_folds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    train_window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    test_window_days: Mapped[int] = mapped_column(Integer, nullable=False)

    total_predictions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_trades_simulated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    win_rate_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))
    accuracy_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))
    precision_at_5: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))
    precision_at_10: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))

    total_return_pct: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal('0'))
    sharpe_ratio: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))
    max_drawdown_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))
    avg_trade_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))

    long_accuracy_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))
    short_accuracy_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))

    fold_metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # Per-fold breakdown
    model_comparison: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # RF vs LGB vs XGB performance

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BacktestPosition(Base):
    """Stores each simulated trade position from backtesting."""

    __tablename__ = 'backtest_positions'
    __table_args__ = (
        Index('ix_backtest_positions_backtest_run_id', 'backtest_run_id'),
        Index('ix_backtest_positions_security_date', 'security_id', 'entry_date'),
        Index('ix_backtest_positions_pnl', 'realized_pnl_pct'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backtest_run_id: Mapped[int] = mapped_column(ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False)
    security_id: Mapped[int] = mapped_column(ForeignKey('securities.id', ondelete='CASCADE'), nullable=False)

    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # 'long' or 'short'
    confidence: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)

    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    position_size: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    stop_loss_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    take_profit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)  # Unused with trailing-stop strategy

    exit_date: Mapped[date] = mapped_column(Date, nullable=True)
    exit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 'stop_loss', 'take_profit', 'timeout', 'manual'

    target_move_pct: Mapped[float] = mapped_column(default=5.0)
    actual_move_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    hit: Mapped[bool | None] = mapped_column(nullable=True)  # Did prediction come true?

    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0'))
    realized_pnl_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))

    days_held: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BacktestPrediction(Base):
    """Stores predicted vs actual outcome for each stock-date from backtesting."""

    __tablename__ = 'backtest_predictions'
    __table_args__ = (
        UniqueConstraint('backtest_run_id', 'prediction_date', 'security_id', 'direction', name='uq_backtest_pred_date_sec_dir'),
        Index('ix_backtest_predictions_backtest_run_id', 'backtest_run_id'),
        Index('ix_backtest_predictions_date_direction', 'prediction_date', 'direction'),
        Index('ix_backtest_predictions_hit', 'hit'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backtest_run_id: Mapped[int] = mapped_column(ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False)
    security_id: Mapped[int] = mapped_column(ForeignKey('securities.id', ondelete='CASCADE'), nullable=False)

    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # 'long' or 'short'

    predicted_confidence: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    predicted_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    threshold_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('5.0'))

    actual_move_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    hit: Mapped[bool | None] = mapped_column(nullable=True)  # Did it move as predicted?

    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    top_features: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BacktestDailyMetrics(Base):
    """Stores daily snapshots of portfolio performance during backtesting."""

    __tablename__ = 'backtest_daily_metrics'
    __table_args__ = (
        UniqueConstraint('backtest_run_id', 'metric_date', name='uq_backtest_daily_date'),
        Index('ix_backtest_daily_backtest_run_id', 'backtest_run_id'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backtest_run_id: Mapped[int] = mapped_column(ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False)

    metric_date: Mapped[date] = mapped_column(Date, nullable=False)

    portfolio_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cumulative_return_pct: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    daily_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    max_drawdown_to_date_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    open_positions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    closed_positions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    trades_won_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trades_lost_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BacktestEnsembleTraining(Base):
    """Stores per-fold ensemble model training results during walk-forward validation."""

    __tablename__ = 'backtest_ensemble_training'
    __table_args__ = (
        UniqueConstraint('backtest_run_id', 'fold_number', name='uq_backtest_ensemble_fold'),
        Index('ix_backtest_ensemble_backtest_run_id', 'backtest_run_id'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backtest_run_id: Mapped[int] = mapped_column(ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False)

    fold_number: Mapped[int] = mapped_column(Integer, nullable=False)
    fold_name: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g., 'fold_1_2024-01-01_to_2025-01-01'

    train_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    train_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    test_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    test_end_date: Mapped[date] = mapped_column(Date, nullable=False)

    train_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    test_samples: Mapped[int] = mapped_column(Integer, nullable=False)

    # Model paths (joblib artifacts)
    rf_model_path: Mapped[str] = mapped_column(String(512), nullable=True)
    lgb_model_path: Mapped[str] = mapped_column(String(512), nullable=True)
    xgb_model_path: Mapped[str] = mapped_column(String(512), nullable=True)

    # Per-model validation metrics
    rf_accuracy: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    rf_precision_at_5: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    rf_sharpe: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)

    lgb_accuracy: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    lgb_precision_at_5: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    lgb_sharpe: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)

    xgb_accuracy: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    xgb_precision_at_5: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    xgb_sharpe: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)

    # Ensemble voting result
    ensemble_accuracy: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    ensemble_precision_at_5: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    ensemble_sharpe: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    long_accuracy: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    short_accuracy: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    model_comparison: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
