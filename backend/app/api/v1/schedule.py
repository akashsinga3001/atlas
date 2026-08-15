# backend/app/api/v1/schedule.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError, ValidationError
from app.services.schedule import ScheduleService
from app.schemas.base import APIResponse
from app.schemas.schedule import CreateScheduleEntryRequest, UpdateScheduleEntryRequest, ToggleScheduleEntryRequest
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=APIResponse)
async def list_entries(db: Session = Depends(get_db)) -> APIResponse:
    """Return all schedule entries."""
    try:
        data = ScheduleService(db).list_entries()
        return APIResponse(success=True, message="Schedule entries retrieved successfully.", data=data)
    except Exception as exc:
        logger.error(f"Failed to retrieve schedule entries. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to retrieve schedule entries.", errors={ "detail": str(exc) })


@router.post("", response_model=APIResponse)
async def create_entry(request: CreateScheduleEntryRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Create a new schedule entry and push it to RedBeat."""
    try:
        data = ScheduleService(db).create_entry(request)
        return APIResponse(success=True, message="Schedule entry created.", data=data)
    except (NotFoundError, ValidationError) as exc:
        return APIResponse(success=False, message=exc.message, errors=exc.details)
    except Exception as exc:
        logger.error(f"Failed to create schedule entry. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to create schedule entry.", errors={ "detail": str(exc) })


@router.patch("/{entry_id}", response_model=APIResponse)
async def update_entry(entry_id: int, request: UpdateScheduleEntryRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Update a schedule entry's cron fields, kwargs, or metadata and re-sync it to RedBeat."""
    try:
        data = ScheduleService(db).update_entry(entry_id, request)
        return APIResponse(success=True, message="Schedule entry updated.", data=data)
    except (NotFoundError, ValidationError) as exc:
        return APIResponse(success=False, message=exc.message, errors=exc.details)
    except Exception as exc:
        logger.error(f"Failed to update schedule entry {entry_id}. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to update schedule entry.", errors={ "detail": str(exc) })


@router.post("/{entry_id}/toggle", response_model=APIResponse)
async def toggle_entry(entry_id: int, request: ToggleScheduleEntryRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Enable or disable a schedule entry — takes effect within one beat tick, no restart."""
    try:
        data = ScheduleService(db).toggle_enabled(entry_id, request.enabled)
        return APIResponse(success=True, message="Schedule entry updated.", data=data)
    except NotFoundError as exc:
        return APIResponse(success=False, message=exc.message, errors=exc.details)
    except Exception as exc:
        logger.error(f"Failed to toggle schedule entry {entry_id}. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to toggle schedule entry.", errors={ "detail": str(exc) })


@router.delete("/{entry_id}", response_model=APIResponse)
async def delete_entry(entry_id: int, db: Session = Depends(get_db)) -> APIResponse:
    """Delete a schedule entry from Postgres and RedBeat."""
    try:
        ScheduleService(db).delete_entry(entry_id)
        return APIResponse(success=True, message="Schedule entry deleted.")
    except NotFoundError as exc:
        return APIResponse(success=False, message=exc.message, errors=exc.details)
    except Exception as exc:
        logger.error(f"Failed to delete schedule entry {entry_id}. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to delete schedule entry.", errors={ "detail": str(exc) })


@router.post("/resync", response_model=APIResponse)
async def resync_all(db: Session = Depends(get_db)) -> APIResponse:
    """Push every schedule entry from Postgres into RedBeat — recovery path if Redis and Postgres ever drift."""
    try:
        data = ScheduleService(db).resync_all()
        return APIResponse(success=True, message="Schedule resynced.", data=data)
    except Exception as exc:
        logger.error(f"Failed to resync schedule. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to resync schedule.", errors={ "detail": str(exc) })
