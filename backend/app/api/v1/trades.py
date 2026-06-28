# backend/app/api/v1/trades.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.enums.trade import TradeStatus
from app.services.trade import TradeService
from app.schemas.base import APIResponse
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=APIResponse)
async def get_trades(status: Optional[str] = Query(None, description="Filter trades by status"), db: Session = Depends(get_db)):
    """Return all trades, optionally filtered by status."""
    try:
        trade_status = TradeStatus(status) if status else None
        data = TradeService(db).get_trades(status=trade_status)
        return APIResponse(success=True, message="Trades retrieved", data=data)
    except ValueError:
        return APIResponse(success=False, message=f"Invalid status: {status}")
    except Exception as exc:
        logger.error("Error fetching trades: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))
