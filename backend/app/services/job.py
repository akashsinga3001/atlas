# backend/app/services/job.py

from app.schemas.base import APIResponse
from app.enums.job import JobType
from app.schemas.job import JobTriggerRequest
from app.schemas.ohlcv import OHLCVImportRequest

# Job Imports
from app.jobs.refresh_broker_token import refresh_kite_token
from app.jobs.securities_import import import_securities
from app.jobs.ohlcv_import import import_ohlcv_data

from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobService:
    """Service class for managing background jobs and scheduled tasks."""

    def __init__(self):
        self.job_parameters_map = {JobType.OHLCV_IMPORT: OHLCVImportRequest}
        self.job_execution_map = {JobType.KITE_TOKEN_REFRESH: refresh_kite_token, JobType.SECURITIES_IMPORT: import_securities, JobType.OHLCV_IMPORT: import_ohlcv_data}
        pass

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
