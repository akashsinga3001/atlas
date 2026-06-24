# backend/app/services/strategy.py

from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional

from app.models.strategy import StrategyRun, StrategySignal, StrategyVersion
from app.enums.strategy import StrategyRunStatus
from app.strategies.context import StrategyContext
from app.strategies.registry import StrategyRegistry
from app.services.feature import FeatureService
from app.schemas.base import APIResponse


class StrategyService:
    """Service for managing strategy runs and signals."""

    def __init__(self, db: Session):
        self.db = db

    def run(self, strategy_version_id: int, as_of_date: Optional[datetime] = None) -> APIResponse:
        """Run a strategy version and create a strategy run record."""
        strategy_version = self.db.query(StrategyVersion).filter(StrategyVersion.id == strategy_version_id).first()
        if not strategy_version:
            raise ValueError(f"Strategy version with id {strategy_version_id} not found")

        strategy_class = StrategyRegistry.get(strategy_version.implementation_class)
        strategy = strategy_class()
        strategy_run = StrategyRun(strategy_version_id=strategy_version.id, status=StrategyRunStatus.PENDING)

        self.db.add(strategy_run)
        self.db.commit()
        self.db.refresh(strategy_run)

        try:
            strategy_run.status = StrategyRunStatus.RUNNING
            strategy_run.started_at = datetime.utcnow()
            self.db.commit()

            context = StrategyContext(as_of_date=as_of_date or datetime.utcnow(), config=strategy_version.config, feature_service=FeatureService(self.db))
            observations = strategy.execute(context)

            for observation in observations:
                signal = StrategySignal(strategy_run_id=strategy_run.id, observed_at=observation.observed_at, payload=observation.payload, security_id=observation.security_id)
                self.db.add(signal)

            strategy_run.signal_count = len(observations)
            strategy_run.completed_at = datetime.utcnow()
            strategy_run.status = StrategyRunStatus.COMPLETED
            self.db.commit()

            return APIResponse(success=True, message="Strategy run completed successfully", data={ "strategy_run_id": strategy_run.id })
        except Exception as exc:
            strategy_run.status = StrategyRunStatus.FAILED
            strategy_run.completed_at = datetime.utcnow()
            strategy_run.error_message = str(exc)
            self.db.commit()
            return APIResponse(success=False, message="Strategy run failed", data={ "strategy_run_id": strategy_run.id, "error_message": strategy_run.error_message })
