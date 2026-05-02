"""Derived candle feature model for OHLCV records."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Feature(Base):
    __tablename__ = 'features'
    __table_args__ = (UniqueConstraint('ohlcv_id', name='uq_features_ohlcv_id'), )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ohlcv_id: Mapped[int] = mapped_column(ForeignKey('ohlcv.id', ondelete='CASCADE'), nullable=False, index=True)

    body_size_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    upper_wick_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    lower_wick_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    range_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    close_position_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    bias: Mapped[str] = mapped_column(String(16), nullable=False)
    candle_type: Mapped[str] = mapped_column(String(64), nullable=False)

    volatility_10d: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    volatility_20d: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    volatility_ratio_10_20: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    close_vs_sma10_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    close_vs_sma20_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    close_vs_sma50_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    sma10_slope: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    sma20_slope: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    sma50_slope: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    uptrend_alignment: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    volume_zscore_20d: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    volume_ratio_5_20: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    roc_5d: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    roc_10d: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    roc_20d: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    rsi_14: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    stochastic_k_14: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    dist_from_20d_high_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    dist_from_20d_low_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    dist_from_52w_high_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    dist_from_52w_low_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
