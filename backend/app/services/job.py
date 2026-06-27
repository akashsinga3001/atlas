# backend/app/services/job.py

from sqlalchemy.orm import Session

from app.schemas.base import APIResponse
from app.enums.job import JobType
from app.schemas.job import JobTriggerRequest
from app.schemas.ohlcv import OHLCVImportRequest
from app.schemas.feature import FeatureCalculationRequest
from app.schemas.strategy import StrategyExecutionRequest
from app.models.job import JobRun

# Job Imports
from app.jobs.refresh_broker_token import refresh_kite_token
from app.jobs.securities_import import import_securities
from app.jobs.ohlcv_import import import_ohlcv_data
from app.jobs.enrich_securities import enrich_securities
from app.jobs.feature_generation import generate_features
from app.jobs.strategy_execution import execute_strategy
from app.jobs.trade_entry import run_trade_entry
from app.jobs.trade_exit import run_trade_exit
from app.jobs.trade_reconciliation import run_trade_reconciliation
from app.jobs.position_sync import run_position_sync

from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobService:
    """Service class for managing background jobs and scheduled tasks."""

    def __init__(self):
        self.job_parameters_map = {JobType.OHLCV_IMPORT: OHLCVImportRequest, JobType.FEATURE_GENERATION: FeatureCalculationRequest, JobType.STRATEGY_EXECUTION: StrategyExecutionRequest, JobType.TRADE_ENTRY: StrategyExecutionRequest, JobType.TRADE_EXIT: StrategyExecutionRequest}
        self.job_execution_map = {JobType.KITE_TOKEN_REFRESH: refresh_kite_token, JobType.SECURITIES_IMPORT: import_securities, JobType.OHLCV_IMPORT: import_ohlcv_data, JobType.SECURITIES_ENRICHMENT: enrich_securities, JobType.FEATURE_GENERATION: generate_features, JobType.STRATEGY_EXECUTION: execute_strategy, JobType.TRADE_ENTRY: run_trade_entry, JobType.TRADE_EXIT: run_trade_exit, JobType.TRADE_RECONCILIATION: run_trade_reconciliation, JobType.POSITION_SYNC: run_position_sync}

    def get_last_runs(self, db: Session) -> dict[str, dict]:
        """Return the most recent JobRun record per job_name."""
        subq = (db.query(JobRun.job_name, JobRun.started_at, JobRun.status, JobRun.duration_seconds, JobRun.error_message).distinct(JobRun.job_name).order_by(JobRun.job_name, JobRun.started_at.desc()).subquery())
        rows = db.query(subq).all()
        return {row.job_name: { "last_run_at": row.started_at.isoformat() if row.started_at else None, "last_run_status": row.status, "last_run_duration": row.duration_seconds, "last_run_error": row.error_message, } for row in rows}

    def execute_job(self, request: JobTriggerRequest, db=None) -> APIResponse:
        """Execute a specific job by name."""
        logger.info(f"Executing job: {request.job_name}")
        try:
            job_type = JobType[request.job_name]
            job_parameters = self.job_parameters_map.get(job_type)

            if job_parameters:
                validated_params = job_parameters.model_validate(request.parameters or {})
                task_args = validated_params.model_dump(exclude_none=True)
            else:
                task_args = request.parameters or {}

            celery_task = self.job_execution_map.get(job_type)
            if not celery_task:
                logger.error(f"Unknown job type: {request.job_name}")
                raise ValueError(f"Unknown job type: {request.job_name}")
            celery_task.apply_async(kwargs=task_args)
        except Exception as exc:
            logger.error(f"Error executing job '{request.job_name}': {exc}", exc_info=True)
            raise
