# backend/app/api/v1/signals.py

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.signal import SignalService
from app.schemas.base import APIResponse
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=APIResponse)
async def get_signals(date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None), status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    try:
        service = SignalService(db)
        result = service.get_signals(date_from=date_from, date_to=date_to, status=status)
        return APIResponse(success=True, message="Signals retrieved", data=result)
    except Exception as exc:
        logger.error("Error fetching signals: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))


@router.get("/{signal_id}/performance", response_model=APIResponse)
async def get_signal_performance(signal_id: int, db: Session = Depends(get_db)):
    try:
        service = SignalService(db)
        result = service.get_performance(signal_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Signal not found")
        return APIResponse(success=True, message="Signal performance retrieved", data=result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching signal performance for {}: {}", signal_id, exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))
