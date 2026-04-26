"""OHLCV candle model for multi-timeframe market data."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Ohlcv(Base):
    __tablename__ = 'ohlcv'
    __table_args__ = (
        UniqueConstraint('security_id', 'timeframe', 'candle_date', name='uq_ohlcv_security_timeframe_candle_date'),
        Index('ix_ohlcv_timeframe_candle_date', 'timeframe', 'candle_date'),
        Index('ix_ohlcv_security_timeframe', 'security_id', 'timeframe'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    security_id: Mapped[int] = mapped_column(ForeignKey('securities.id', ondelete='CASCADE'), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    candle_date: Mapped[date] = mapped_column(Date, nullable=False)

    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    is_continuous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default='kite')

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
