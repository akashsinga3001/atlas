# backend/app/models/fund.py

from datetime import date, datetime
from sqlalchemy import BigInteger, Date, DateTime, Enum, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.enums.fund import FlowType
from .base import Base


class CashFlow(Base):
    __tablename__ = "cash_flows"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    flow_type: Mapped[FlowType] = mapped_column(Enum(FlowType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    flow_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    note: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"
    __table_args__ = (UniqueConstraint("snapshot_date", name="uix_account_snapshot_date"), )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cash_balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    holdings_value: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    total_value: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
