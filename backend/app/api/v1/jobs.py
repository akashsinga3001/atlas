# backend/app/api/v1/jobs.py

from re import A
from fastapi import APIRouter, Query

from app.services.job import JobService
from app.schemas.base import APIResponse
from app.utils.logger import get_logger
from app.enums.job import JobType

router = APIRouter()
logger = get_logger(__name__)


@router.get("/trigger", response_model=APIResponse)
async def trigger_job(job: str = Query(..., description="Name of the job to trigger")) -> APIResponse:
    """Endpoint to trigger a specific job by name."""
    try:
        logger.info(f"Received request to trigger job: {job}")
        job_service = JobService()
        job_service.execute_job(JobType[job])
        return APIResponse(success=True, message=f"Job '{job}' triggered successfully.")
    except Exception as exc:
        logger.error(f"Failed to trigger job '{job}'.", exc_info=True)
        return APIResponse(success=False, message=f"Failed to trigger job '{job}'.", errors={ "detail": str(exc) })
