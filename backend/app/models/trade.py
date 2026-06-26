# backend/app/models/trade.py

from datetime import date
from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Integer, JSON, Numeric, String, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.trade import TradeStatus, ExitReason
from .base import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    strategy_signal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("strategy_signals.id"), nullable=False, index=True)
    strategy_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("strategy_versions.id"), nullable=False, index=True)
    security_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("securities.id"), nullable=False, index=True)

    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    fill_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True)
    fill_quantity: Mapped[int] = mapped_column(Integer, nullable=True)

    kite_entry_order_id: Mapped[str] = mapped_column(String(100), nullable=True)
    kite_gtt_id: Mapped[str] = mapped_column(String(100), nullable=True)
    timeout_date: Mapped[date] = mapped_column(Date, nullable=False)

    state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[TradeStatus] = mapped_column(Enum(TradeStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=TradeStatus.PENDING)
    exit_date: Mapped[date] = mapped_column(Date, nullable=True)
    exit_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True)
    exit_reason: Mapped[ExitReason] = mapped_column(Enum(ExitReason, values_callable=lambda x: [e.value for e in x]), nullable=True)

    security = relationship("Security", lazy="joined")
    strategy_version = relationship("StrategyVersion", lazy="select")
    snapshots: Mapped[list["TradeSnapshot"]] = relationship("TradeSnapshot", back_populates="trade", passive_deletes=True)


class TradeSnapshot(Base):
    __tablename__ = "trade_snapshots"
    __table_args__ = (UniqueConstraint("trade_id", "snapshot_date", name="uix_trade_snapshot_date"), )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("trades.id"), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    close_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    mtm_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    days_held: Mapped[int] = mapped_column(Integer, nullable=False)
    exit_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    trade: Mapped["Trade"] = relationship("Trade", back_populates="snapshots")
