# backend/app/models/circuit_breaker.py

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CircuitBreaker(Base):
    """A tunable, independently-toggleable automatic risk rule (drawdown, consecutive-loss, gap-check, ...)."""
    __tablename__ = "circuit_breakers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
