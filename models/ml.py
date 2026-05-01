"""Persistent models for ML training runs, predictions, and reports."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class MlTrainingRun(Base):
    """Stores one weekly model training run and its evaluation metadata."""

    __tablename__ = 'ml_training_runs'
    __table_args__ = (
        UniqueConstraint('run_date', name='uq_ml_training_runs_run_date'),
        Index('ix_ml_training_runs_status_created_at', 'status', 'created_at'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='completed')
    universe: Mapped[str] = mapped_column(String(16), nullable=False, default='EQ')

    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    threshold_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    samples_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    samples_train: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    samples_validation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    long_positive_rate_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))
    short_positive_rate_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal('0'))

    long_metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    short_metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    feature_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    feature_statistics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    long_feature_importance: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    short_feature_importance: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)

    long_model_path: Mapped[str] = mapped_column(String(512), nullable=False)
    short_model_path: Mapped[str] = mapped_column(String(512), nullable=False)

    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MlPrediction(Base):
    """Stores per-stock directional confidence scores for one report date."""

    __tablename__ = 'ml_predictions'
    __table_args__ = (
        UniqueConstraint('prediction_date', 'security_id', 'direction', name='uq_ml_predictions_date_security_direction'),
        Index('ix_ml_predictions_date_direction_confidence', 'prediction_date', 'direction', 'confidence'),
        Index('ix_ml_predictions_training_run_id', 'training_run_id'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    training_run_id: Mapped[int] = mapped_column(ForeignKey('ml_training_runs.id', ondelete='CASCADE'), nullable=False)
    security_id: Mapped[int] = mapped_column(ForeignKey('securities.id', ondelete='CASCADE'), nullable=False, index=True)

    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)

    confidence: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    threshold_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    top_features: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MlReport(Base):
    """Stores final daily report and email delivery metadata."""

    __tablename__ = 'ml_reports'
    __table_args__ = (
        UniqueConstraint('report_date', name='uq_ml_reports_report_date'),
        Index('ix_ml_reports_status_created_at', 'status', 'created_at'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    training_run_id: Mapped[int] = mapped_column(ForeignKey('ml_training_runs.id', ondelete='CASCADE'), nullable=False)

    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    email_to: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='generated')

    top_long: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    top_short: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    html_body: Mapped[str] = mapped_column(Text, nullable=False)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
