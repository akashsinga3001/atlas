# backend/app/models/schedule.py

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    task: Mapped[str] = mapped_column(String(255), nullable=False)
    minute: Mapped[str] = mapped_column(String(100), nullable=False, default="*")
    hour: Mapped[str] = mapped_column(String(100), nullable=False, default="*")
    day_of_week: Mapped[str] = mapped_column(String(100), nullable=False, default="*")
    day_of_month: Mapped[str] = mapped_column(String(100), nullable=False, default="*")
    month_of_year: Mapped[str] = mapped_column(String(100), nullable=False, default="*")
    kwargs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    group: Mapped[str] = mapped_column(String(50), nullable=False, default="trading")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
