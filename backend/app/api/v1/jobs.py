# backend/app/api/v1/jobs.py

from fastapi import APIRouter, Depends
from requests import Session

from app.services.job import JobService
from app.schemas.base import APIResponse
from app.schemas.job import JobTriggerRequest
from app.utils.logger import get_logger
from app.core.database import get_db

router = APIRouter()
logger = get_logger(__name__)

# yapf: disable
JOB_DEFINITIONS =[
    {"name": "KITE_TOKEN_REFRESH", "display_name": "Kite Token Refresh", "schedule": "Daily 07:45", "description": "Refreshes Kite API access token via Selenium"},
    {"name": "SECURITIES_IMPORT", "display_name": "Securities Import", "schedule": "Daily 08:00", "description": "Imports all active securities from Kite"},
    {"name": "SECURITIES_ENRICHMENT", "display_name": "Securities Enrichment", "schedule": "Monthly 08:30", "description": "Enriches securities with sector and industry metadata"},
    {"name": "OHLCV_IMPORT", "display_name": "OHLCV Import", "schedule": "Daily 08:00 + Live every 5m", "description": "Imports OHLCV candle data from Kite"},
    {"name": "FEATURE_GENERATION", "display_name": "Feature Generation", "schedule": "Daily 16:30 + Live every 5m", "description": "Computes technical features for all securities"},
    {"name": "STRATEGY_EXECUTION", "display_name": "Strategy Execution", "schedule": "On-demand", "description": "Runs momentum screener and generates signals"},
    {"name": "POSITION_SYNC", "display_name": "Position Sync", "schedule": "Weekdays 15:20", "description": "Syncs open positions against Kite holdings"},
    {"name": "TRADE_EXIT", "display_name": "Trade Exit", "schedule": "Weekdays 15:25", "description": "Evaluates exit conditions and updates GTT stops"},
    {"name": "TRADE_ENTRY", "display_name": "Trade Entry", "schedule": "Weekdays 15:27", "description": "Places buy orders for new signals"},
    {"name": "TRADE_RECONCILIATION", "display_name": "Trade Reconciliation", "schedule": "Weekdays 16:00", "description": "Resolves pending orders against Kite order history"}
]
# yapf: enable


@router.get("", response_model=APIResponse)
async def getjobs() -> APIResponse:
    """Endpoint to retrieve all available job definitions."""
    try:
        return APIResponse(success=True, message="Job definitions retrieved successfully.", data=JOB_DEFINITIONS)
    except Exception as exc:
        logger.error(f"Failed to retrieve job definitions. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to retrieve job definitions.", errors={ "detail": str(exc) })


@router.post("/trigger", response_model=APIResponse)
async def trigger_job(request: JobTriggerRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Endpoint to trigger a specific job by name."""
    try:
        logger.info(f"Received request to trigger job: {request.job_name}")
        job_service = JobService()
        job_service.execute_job(request, db=db)
        return APIResponse(success=True, message=f"Job '{request.job_name}' triggered successfully.")
    except Exception as exc:
        logger.error(f"Failed to trigger job '{request.job_name}'. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message=f"Failed to trigger job '{request.job_name}'.", errors={ "detail": str(exc) })
