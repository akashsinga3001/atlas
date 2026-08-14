# backend/app/models/options.py

from datetime import date, datetime
from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.options import OptionsPositionStatus, OptionsLegRole, OptionsLegStatus, OptionsExitReason
from .base import Base


class OptionsPosition(Base):
    __tablename__ = "options_positions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    strategy_signal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("strategy_signals.id"), nullable=False, unique=True, index=True)
    strategy_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("strategy_versions.id"), nullable=False, index=True)

    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    spot_at_signal: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)

    expiry_date: Mapped[date] = mapped_column(Date, nullable=True)
    call_short_strike: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True)
    put_short_strike: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True)
    call_long_strike: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True)
    put_long_strike: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True)

    lots: Mapped[int] = mapped_column(Integer, nullable=True)
    lot_size: Mapped[int] = mapped_column(Integer, nullable=True)
    margin_per_lot: Mapped[float] = mapped_column(Numeric(14, 4), nullable=True)
    net_credit_per_lot: Mapped[float] = mapped_column(Numeric(14, 4), nullable=True)

    status: Mapped[OptionsPositionStatus] = mapped_column(Enum(OptionsPositionStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=OptionsPositionStatus.PENDING)
    skip_reason: Mapped[str] = mapped_column(String(255), nullable=True)

    planned_exit_date: Mapped[date] = mapped_column(Date, nullable=True)
    exit_date: Mapped[date] = mapped_column(Date, nullable=True)
    exit_reason: Mapped[OptionsExitReason] = mapped_column(Enum(OptionsExitReason, values_callable=lambda x: [e.value for e in x]), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    strategy_version = relationship("StrategyVersion", lazy="select")
    legs: Mapped[list["OptionsLeg"]] = relationship("OptionsLeg", back_populates="options_position", passive_deletes=True)


class OptionsLeg(Base):
    __tablename__ = "options_legs"
    __table_args__ = (UniqueConstraint("options_position_id", "role", name="uix_options_leg_position_role"), )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    options_position_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("options_positions.id"), nullable=False, index=True)
    security_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("securities.id"), nullable=False, index=True)

    role: Mapped[OptionsLegRole] = mapped_column(Enum(OptionsLegRole, values_callable=lambda x: [e.value for e in x]), nullable=False)
    status: Mapped[OptionsLegStatus] = mapped_column(Enum(OptionsLegStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=OptionsLegStatus.PENDING)

    kite_entry_order_id: Mapped[str] = mapped_column(String(100), nullable=True)
    entry_fill_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True)
    entry_fill_quantity: Mapped[int] = mapped_column(Integer, nullable=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=True)

    kite_exit_order_id: Mapped[str] = mapped_column(String(100), nullable=True)
    exit_fill_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True)
    exit_fill_quantity: Mapped[int] = mapped_column(Integer, nullable=True)
    exit_date: Mapped[date] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    security = relationship("Security", lazy="joined")
    options_position: Mapped["OptionsPosition"] = relationship("OptionsPosition", back_populates="legs")
