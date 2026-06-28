# backend/app/api/v1/signals.py

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.signal import SignalService
from app.schemas.base import APIResponse
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=APIResponse)
async def get_signals(date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None), status: Optional[str] = Query(None), strategy: Optional[str] = Query(None), db: Session = Depends(get_db), ):
    """Return all signals with trade and performance data, supporting optional filters."""
    try:
        result = SignalService(db).get_signals(date_from=date_from, date_to=date_to, status=status, strategy=strategy)
        return APIResponse(success=True, message="Signals retrieved", data=result)
    except Exception as exc:
        logger.error("Error fetching signals: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))


@router.get("/{signal_id}/performance", response_model=APIResponse)
async def get_signal_performance(signal_id: int, db: Session = Depends(get_db)):
    """Return forward performance data and trade details for a single signal."""
    try:
        result = SignalService(db).get_performance(signal_id)
        if result is None:
            return APIResponse(success=False, message="Signal not found")
        return APIResponse(success=True, message="Signal performance retrieved", data=result)
    except Exception as exc:
        logger.error("Error fetching signal performance for {}: {}", signal_id, exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))
