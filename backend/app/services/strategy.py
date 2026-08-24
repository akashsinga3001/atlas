# backend/app/services/strategy.py

from datetime import date, datetime, time
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session
from typing import Optional

from app.models.strategy import Strategy, StrategyRun, StrategySignal, StrategyVersion
from app.enums.strategy import StrategyRunStatus
from app.strategies.context import StrategyContext
from app.strategies.registry import StrategyRegistry
from app.repositories.strategy import StrategyRepository, StrategyVersionRepository
from app.repositories.trade import TradeRepository
from app.repositories.options import OptionsPositionRepository
from app.schemas.strategy import StrategyResponse, StrategyRunResponse, StrategyVersionResponse
from app.schemas.strategy_config import get_config_schema
from app.services.feature import FeatureService
from app.services.quote import QuoteService
from app.schemas.base import APIResponse
from app.core.exceptions import NotFoundError, ValidationError
from app.utils.pydantic_forms import schema_to_fields
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StrategyService:
    """Service for managing strategy runs, signals, and versioned config."""

    def __init__(self, db: Session):
        self.db = db
        self.strategy_repo = StrategyRepository(db)
        self.version_repo = StrategyVersionRepository(db)
        self.trade_repo = TradeRepository(db)
        self.options_position_repo = OptionsPositionRepository(db)

    # ------------------------------------------------------------------ #
    #  Config listing / versioning                                        #
    # ------------------------------------------------------------------ #

    def list_strategies(self) -> list[dict]:
        """Return every strategy with its active version, config field schema, and version count."""
        strategies = self.strategy_repo.get_all_with_versions()
        return [self._build_strategy_response(s) for s in strategies]

    def _build_strategy_response(self, strategy: Strategy) -> dict:
        """Serialise a strategy, its active version, its config field schema (if registered), and a live status summary to a dict."""
        active = self.version_repo.get_active_for_strategy(strategy.id)
        schema_cls = get_config_schema(active.implementation_class) if active else None

        if strategy.execution_engine == "options_iron_condor":
            open_positions_count = self.options_position_repo.count_active_for_strategy(strategy.id)
        else:
            open_positions_count = self.trade_repo.count_active_trades_for_strategy(strategy.id)

        last_run = self._get_last_run(strategy.id)

        return StrategyResponse(
            id=strategy.id, code=strategy.code, name=strategy.name, is_active=strategy.is_active,
            has_config_schema=schema_cls is not None,
            config_fields=schema_to_fields(schema_cls) if schema_cls else [],
            active_version=self._build_version_response(active) if active else None,
            version_count=len(strategy.versions),
            open_positions_count=open_positions_count,
            last_run_status=last_run.status if last_run else None,
            last_run_at=(last_run.completed_at or last_run.started_at) if last_run else None,
        ).model_dump()

    def _get_last_run(self, strategy_id: int) -> Optional[StrategyRun]:
        """Fetch the most recent strategy run across every version of a strategy, if any."""
        return self.version_repo.get_last_run_for_strategy(strategy_id)

    def _build_version_response(self, version: StrategyVersion) -> dict:
        """Serialise a single strategy version to a dict."""
        return StrategyVersionResponse(
            id=version.id, strategy_id=version.strategy_id, version=version.version, config=version.config,
            implementation_class=version.implementation_class, exit_evaluator_class=version.exit_evaluator_class,
            is_active=version.is_active, created_at=version.created_at,
        ).model_dump()

    def get_version_history(self, strategy_id: int) -> list[dict]:
        """Return all versions of a strategy, newest first."""
        strategy = self.strategy_repo.get_by_id(strategy_id)
        if not strategy:
            raise NotFoundError(resource="Strategy", identifier=str(strategy_id))
        return [self._build_version_response(v) for v in self.version_repo.get_all_for_strategy(strategy_id)]

    def get_run_history(self, strategy_id: int, limit: int = 20) -> list[dict]:
        """Return the most recent strategy runs across every version of a strategy, newest first."""
        strategy = self.strategy_repo.get_by_id(strategy_id)
        if not strategy:
            raise NotFoundError(resource="Strategy", identifier=str(strategy_id))
        return [self._build_run_response(r) for r in self.version_repo.get_recent_runs_for_strategy(strategy_id, limit)]

    def _build_run_response(self, run: StrategyRun) -> dict:
        """Serialise a strategy run to a dict."""
        return StrategyRunResponse(
            id=run.id, strategy_version_id=run.strategy_version_id, version=run.strategy_version.version, status=run.status,
            started_at=run.started_at, completed_at=run.completed_at, signal_count=run.signal_count, error_message=run.error_message,
        ).model_dump()

    def set_active(self, strategy_id: int, is_active: bool) -> dict:
        """Enable or disable a strategy — checked by strategy_execution/trade_entry jobs; exits are never gated by this."""
        strategy = self.strategy_repo.get_by_id(strategy_id)
        if not strategy:
            raise NotFoundError(resource="Strategy", identifier=str(strategy_id))

        self.strategy_repo.update(strategy, {"is_active": is_active})
        return self._build_strategy_response(strategy)

    def create_version(self, strategy_id: int, config: dict) -> dict:
        """Validate config against the strategy's registered schema (if any) and insert it as a new, inactive version."""
        strategy = self.strategy_repo.get_by_id(strategy_id)
        if not strategy:
            raise NotFoundError(resource="Strategy", identifier=str(strategy_id))

        existing = self.version_repo.get_all_for_strategy(strategy_id)
        if not existing:
            raise ValidationError(message="Cannot create a version — strategy has no baseline version to derive its implementation from")
        current = self.version_repo.get_active_for_strategy(strategy_id) or existing[0]

        schema_cls = get_config_schema(current.implementation_class)
        if schema_cls:
            try:
                config = schema_cls.model_validate(config).model_dump()
            except PydanticValidationError as exc:
                raise ValidationError(message="Config failed schema validation", field_errors=exc.errors())

        next_version = self.version_repo.get_max_version(strategy_id) + 1
        new_version = StrategyVersion(
            strategy_id=strategy_id, version=next_version, config=config,
            implementation_class=current.implementation_class, exit_evaluator_class=current.exit_evaluator_class,
            is_active=False,
        )
        created = self.version_repo.create(new_version)
        return self._build_version_response(created)

    def activate_version(self, strategy_id: int, version_id: int) -> dict:
        """Atomically deactivate every other version of this strategy and activate the given one."""
        locked_strategy = self.strategy_repo.lock_for_update(strategy_id)
        if not locked_strategy:
            raise NotFoundError(resource="Strategy", identifier=str(strategy_id))

        target = self.version_repo.get_by_id(version_id)
        if not target or target.strategy_id != strategy_id:
            raise NotFoundError(resource="StrategyVersion", identifier=str(version_id))

        self.version_repo.deactivate_all_except(strategy_id, version_id)
        target.is_active = True
        self.db.commit()
        self.db.refresh(target)
        return self._build_version_response(target)

    def run(self, strategy_id: int, as_of_date: Optional[datetime] = None) -> APIResponse:
        """Run a strategy's active version and create a strategy run record."""
        strategy_version = self.version_repo.get_active_for_strategy(strategy_id)
        if not strategy_version:
            raise ValueError(f"No active StrategyVersion found for strategy {strategy_id}")

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

            context = StrategyContext(as_of_date=as_of_date or datetime.combine(date.today(), time.max), config=strategy_version.config, feature_service=FeatureService(self.db), quote_service_factory=lambda: QuoteService(self.db))
            observations = strategy.execute(context)

            for observation in observations:
                signal = StrategySignal(strategy_run_id=strategy_run.id, observed_at=observation.observed_at, payload=observation.payload, security_id=observation.security_id)
                self.db.add(signal)

            strategy_run.signal_count = len(observations)
            strategy_run.completed_at = datetime.utcnow()
            strategy_run.status = StrategyRunStatus.COMPLETED
            self.db.commit()

            return APIResponse(success=True, message="Strategy run completed successfully", data={ "strategy_run_id": strategy_run.id, "signals_count": len(observations), "tickers": [o.payload.get("ticker", "") for o in observations if o.payload] })
        except Exception as exc:
            logger.error(f"Strategy execute() raised for strategy {strategy_id}: {str(exc)}", exc_info=True)
            strategy_run.status = StrategyRunStatus.FAILED
            strategy_run.completed_at = datetime.utcnow()
            strategy_run.error_message = str(exc)
            self.db.commit()
            return APIResponse(success=False, message=f"Strategy run failed {exc}", data={ "strategy_run_id": strategy_run.id, "error_message": strategy_run.error_message })
