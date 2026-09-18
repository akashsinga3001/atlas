# backend/app/api/v1/kill_switch.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AtlasException, InternalError
from app.services.kill_switch import KillSwitchService
from app.schemas.base import APIResponse
from app.schemas.kill_switch import ActivateKillSwitchRequest
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=APIResponse)
async def get_status(db: Session = Depends(get_db)) -> APIResponse:
    """Return the current kill-switch state."""
    try:
        data = KillSwitchService(db).get_status()
        return APIResponse(success=True, message="Kill switch status retrieved.", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to retrieve kill switch status. Error: {str(exc)}")
        raise InternalError(message="Failed to retrieve kill switch status.", details={ "detail": str(exc) }) from exc


@router.post("/activate", response_model=APIResponse)
async def activate(request: ActivateKillSwitchRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Pause new-entry jobs."""
    try:
        data = KillSwitchService(db).activate(request.reason)
        return APIResponse(success=True, message="New entries paused.", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to activate kill switch. Error: {str(exc)}")
        raise InternalError(message="Failed to activate kill switch.", details={ "detail": str(exc) }) from exc


@router.post("/deactivate", response_model=APIResponse)
async def deactivate(db: Session = Depends(get_db)) -> APIResponse:
    """Resume new-entry jobs."""
    try:
        data = KillSwitchService(db).deactivate()
        return APIResponse(success=True, message="New entries resumed.", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to deactivate kill switch. Error: {str(exc)}")
        raise InternalError(message="Failed to deactivate kill switch.", details={ "detail": str(exc) }) from exc
