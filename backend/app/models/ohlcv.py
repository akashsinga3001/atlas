# backend/app/models/ohlcv.py

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .features import SecurityFeature


class OHLCV(Base):
    __tablename__ = "ohlcv"
    __table_args__ = (UniqueConstraint("security_id", "candle_timestamp", "timeframe", name="uix_security_timestamp_timeframe"), Index("idx_security_timeframe_timestamp", "security_id", "timeframe", "candle_timestamp"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    security_id: Mapped[int] = mapped_column(Integer, ForeignKey("securities.id"), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(20), nullable=False)
    candle_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[Decimal] = mapped_column(BigInteger, nullable=False, default=0)

    is_continuous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(50), nullable=True, default="kite")
    feature: Mapped["SecurityFeature"] = relationship("SecurityFeature", back_populates="ohlcv", uselist=False, passive_deletes=True)
