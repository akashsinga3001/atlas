"""Persistent models for backtest run summaries and trade logs."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class BacktestRun(Base):
    """Stores one complete backtest run with aggregate metrics."""

    __tablename__ = 'backtest_runs'
    __table_args__ = (
        Index('ix_backtest_runs_strategy_created_at', 'strategy_name', 'created_at'),
        Index('ix_backtest_runs_timeframe_created_at', 'timeframe', 'created_at'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    allow_short: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    transaction_cost_bps: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))
    slippage_bps: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))

    initial_capital: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    final_capital: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    total_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    max_drawdown_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_rate_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    avg_trade_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default='completed')
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BacktestTrade(Base):
    """Stores one executed trade linked to a backtest run."""

    __tablename__ = 'backtest_trades'
    __table_args__ = (
        Index('ix_backtest_trades_run_security', 'backtest_run_id', 'security_id'),
        Index('ix_backtest_trades_direction_exit_date', 'direction', 'exit_date'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backtest_run_id: Mapped[int] = mapped_column(ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    security_id: Mapped[int] = mapped_column(ForeignKey('securities.id', ondelete='CASCADE'), nullable=False, index=True)

    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)

    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    exit_date: Mapped[date] = mapped_column(Date, nullable=False)

    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    exit_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal('1'))

    entry_signal: Mapped[str] = mapped_column(String(32), nullable=False)
    exit_signal: Mapped[str] = mapped_column(String(32), nullable=False)

    gross_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    net_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    bars_held: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    entry_features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    exit_features: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
