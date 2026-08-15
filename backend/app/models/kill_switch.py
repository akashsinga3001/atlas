# backend/app/models/kill_switch.py

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class KillSwitch(Base):
    """Singleton row (id=1) gating whether new-entry jobs are allowed to place orders."""
    __tablename__ = "kill_switch"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
