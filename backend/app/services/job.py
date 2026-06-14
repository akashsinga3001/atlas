# backend/app/services/job.py

from app.schemas.base import APIResponse
from app.enums.job import JobType

# Job Imports
from app.jobs.refresh_broker_token import refresh_kite_token
from app.jobs.securities_import import import_securities

from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobService:
    """Service class for managing background jobs and scheduled tasks."""

    def __init__(self):
        # Initialize any necessary resources, such as database connections or job queues
        pass

    def execute_job(self, job_type: JobType, db=None) -> APIResponse:
        """Execute a specific job by name."""
        logger.info(f"Executing job: {job_type.value}")
        if job_type == JobType.KITE_TOKEN_REFRESH:
            refresh_kite_token.delay()
        elif job_type == JobType.SECURITIES_IMPORT:
            import_securities.delay()
        elif job_type == JobType.SECURITIES_ENRICHMENT:
            logger.warning("Securities enrichment job is not implemented yet.")
        else:
            logger.error(f"Unknown job type: {job_type}")
            raise ValueError(f"Unknown job type: {job_type}")
