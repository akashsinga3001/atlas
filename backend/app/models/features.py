# backend/app/models/features.py

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, Index, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .ohlcv import OHLCV


class FeatureBase(Base):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SecurityFeature(FeatureBase):
    __tablename__ = "security_features"
    __table_args__ = (UniqueConstraint("ohlcv_id", name="uix_security_feature_ohlcv"), Index("idx_security_feature_ohlcv", "ohlcv_id"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ohlcv_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ohlcv.id", ondelete="CASCADE"), nullable=False)

    # Trend Features
    ema_5: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ema_10: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ema_20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ema_50: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ema_100: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    dist_ema_5: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    dist_ema_10: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    dist_ema_20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    dist_ema_50: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ema20_slope_5: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ema50_slope_5: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ema_compression: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    golden_cross: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    dist_252d_low: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    dist_252d_high: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ema_alignment_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_above_ema20: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trend_efficiency: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)

    # Momentum Features
    ret_5: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ret_10: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ret_20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ret_60: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    rsi_14: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    momentum_acceleration: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)

    # Volatility Features
    atr_14: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    atr_pct: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    volatility_20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    bb_width: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    volatility_contraction: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    atr_expansion: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    gap_frequency_20: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_gap_size_20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)

    # Volume Features
    vol_ma_20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    volume_ratio: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    turnover: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    turnover_acceleration: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    avg_turnover_20: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    obv: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    volume_acceleration: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    volume_trend: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    up_volume_ratio: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)

    # Structure Features
    position_in_range: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    near_breakout: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    base_tightness: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    base_width: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    base_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compression_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volatility_contraction_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    up_days_10: Mapped[int | None] = mapped_column(Integer, nullable=True)
    up_days_20: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strong_close_ratio: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    bullish_range_expansion: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    close_near_high: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)

    # Relative Strength Features
    rs_5: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    rs_10: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    rs_20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    rs_60: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    rs_ratio: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    rs_ratio_ret_20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    rs_ratio_ret_60: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)

    # Breakout Features
    dist_20d_high: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    dist_50d_high: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    new_20d_high: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    new_50d_high: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    new_252d_high: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    breakout_strength_20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    breakout_strength_50: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    breakout_volume_ratio: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)

    ohlcv: Mapped["OHLCV"] = relationship("OHLCV", lazy="joined", back_populates="feature", passive_deletes=True)


class SectorFeature(FeatureBase):
    __tablename__ = "sector_features"
    __table_args__ = (UniqueConstraint("sector_name", "timeframe", "candle_timestamp", name="uix_sector_feature"), Index("idx_sector_feature", "sector_name", "timeframe", "candle_timestamp"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sector_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(20), nullable=False)
    candle_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Features
    sector_ret_5: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    sector_ret_10: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    sector_ret_20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    sector_ret_60: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    sector_rs_20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    sector_rs_60: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)


class MarketFeature(FeatureBase):
    __tablename__ = "market_features"
    __table_args__ = (UniqueConstraint("timeframe", "candle_timestamp", name="uix_market_feature"), Index("idx_market_feature", "timeframe", "candle_timestamp"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timeframe: Mapped[str] = mapped_column(String(20), nullable=False)
    candle_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Breadth Features
    advance_decline_ratio: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    market_breadth_ema20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    market_breadth_ema50: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    pct_above_ema20: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    pct_above_ema50: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    pct_above_ema200: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)

    # High-Low Features
    new_highs_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_lows_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Regime Features
    regime_score: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
