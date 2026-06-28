# backend/app/api/v1/jobs.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.job import JobService
from app.schemas.base import APIResponse
from app.schemas.job import JobTriggerRequest
from app.utils.logger import get_logger
from app.core.database import get_db

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=APIResponse)
async def get_jobs(db: Session = Depends(get_db)) -> APIResponse:
    """Return all registered job definitions with their latest run info."""
    try:
        jobs = JobService().get_jobs(db)
        return APIResponse(success=True, message="Job definitions retrieved successfully.", data=jobs)
    except Exception as exc:
        logger.error(f"Failed to retrieve job definitions. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to retrieve job definitions.", errors={ "detail": str(exc) })


@router.post("/trigger", response_model=APIResponse)
async def trigger_job(request: JobTriggerRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Validate and dispatch the named job to Celery for async execution."""
    try:
        logger.info(f"Received request to trigger job: {request.job_name}")
        JobService().execute_job(request, db=db)
        return APIResponse(success=True, message=f"Job '{request.job_name}' triggered successfully.")
    except Exception as exc:
        logger.error(f"Failed to trigger job '{request.job_name}'. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message=f"Failed to trigger job '{request.job_name}'.", errors={ "detail": str(exc) })
