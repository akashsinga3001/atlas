# backend/app/api/v1/market.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.market import MarketService
from app.schemas.base import APIResponse
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/sentiment", response_model=APIResponse)
async def get_market_sentiment(timeframe: str = Query("1d"), db: Session = Depends(get_db)):
    """Return the latest market sentiment snapshot."""
    try:
        sentiment = MarketService(db).get_sentiment(timeframe=timeframe)
        return APIResponse(success=True, message="Sentiment retrieved", data=sentiment)
    except Exception as exc:
        logger.error(f"Error fetching market sentiment: {exc}", exc_info=True)
        return APIResponse(success=False, message=str(exc))


@router.get("/sentiment/history", response_model=APIResponse)
async def get_market_sentiment_history(timeframe: str = Query("1d"), limit: int = Query(60), db: Session = Depends(get_db)):
    """Return recent market sentiment history for trend sparklines."""
    try:
        history = MarketService(db).get_sentiment_history(timeframe=timeframe, limit=limit)
        return APIResponse(success=True, message="Sentiment history retrieved", data=history)
    except Exception as exc:
        logger.error(f"Error fetching market sentiment history: {exc}", exc_info=True)
        return APIResponse(success=False, message=str(exc))
