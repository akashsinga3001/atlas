# backend/app/api/v1/options.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.enums.options import OptionsPositionStatus
from app.services.options_trade import OptionsTradeService
from app.schemas.base import APIResponse
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/positions", response_model=APIResponse)
async def get_positions(status: Optional[str] = Query(None, description="Filter positions by status"), db: Session = Depends(get_db)):
    """Return all iron condor options positions, optionally filtered by status."""
    try:
        position_status = OptionsPositionStatus(status) if status else None
        data = OptionsTradeService(db).get_positions(status=position_status)
        return APIResponse(success=True, message="Options positions retrieved", data=data)
    except ValueError:
        return APIResponse(success=False, message=f"Invalid status: {status}")
    except Exception as exc:
        logger.error("Error fetching options positions: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))
