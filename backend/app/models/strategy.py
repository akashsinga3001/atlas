# backend/app/models/strategy.py

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Index, Integer, String, JSON, ForeignKey, UniqueConstraint, Text, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.strategy import StrategyRunStatus
from .base import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    versions: Mapped[list["StrategyVersion"]] = relationship("StrategyVersion", back_populates="strategy", passive_deletes=True)


class StrategyVersion(Base):
    __tablename__ = "strategy_versions"
    __table_args__ = (UniqueConstraint("strategy_id", "version", name="uix_strategy_version"), )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("strategies.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    implementation_class: Mapped[str] = mapped_column(String(255), nullable=False)
    exit_evaluator_class: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="versions")
    runs: Mapped[list["StrategyRun"]] = relationship("StrategyRun", back_populates="strategy_version", passive_deletes=True)


class StrategyRun(Base):
    __tablename__ = "strategy_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    strategy_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("strategy_versions.id"), nullable=False, index=True)
    status: Mapped[StrategyRunStatus] = mapped_column(Enum(StrategyRunStatus), nullable=False, default=StrategyRunStatus.PENDING)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    signal_count: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    strategy_version: Mapped["StrategyVersion"] = relationship("StrategyVersion", back_populates="runs")
    signals: Mapped[list["StrategySignal"]] = relationship("StrategySignal", back_populates="strategy_run", passive_deletes=True)


class StrategySignal(Base):
    __tablename__ = "strategy_signals"
    __table_args__ = (Index("idx_observed_at_security", "observed_at", "security_id"), )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    strategy_run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("strategy_runs.id"), nullable=False, index=True)
    security_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("securities.id"), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    strategy_run: Mapped["StrategyRun"] = relationship("StrategyRun", back_populates="signals")
    security = relationship("Security", lazy="joined")
