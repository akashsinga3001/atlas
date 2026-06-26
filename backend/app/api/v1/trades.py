# backend/app/api/v1/trades.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.enums.trade import TradeStatus
from app.repositories.trade import TradeRepository
from app.schemas.base import APIResponse
from app.schemas.trade import TradeResponse, SecurityInfo
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _build_response(trade) -> dict:
    invested = None
    pnl = None
    pnl_pct = None

    if trade.fill_price and trade.fill_quantity:
        invested = round(float(trade.fill_price) * trade.fill_quantity, 2)

    if trade.exit_price and trade.fill_price and trade.fill_quantity:
        pnl = round((float(trade.exit_price) - float(trade.fill_price)) * trade.fill_quantity, 2)
        pnl_pct = round((float(trade.exit_price) - float(trade.fill_price)) / float(trade.fill_price) * 100, 4)

    return TradeResponse(
        id=trade.id, security=SecurityInfo(id=trade.security.id, ticker=trade.security.ticker, display_name=trade.security.display_name, sector=trade.security.sector, industry=trade.security.industry), status=trade.status, entry_date=trade.entry_date, fill_price=float(trade.fill_price) if trade.fill_price else None, fill_quantity=trade.fill_quantity, timeout_date=trade.timeout_date, exit_date=trade.exit_date, exit_reason=trade.exit_reason, state=trade.state or {}, invested_value=invested,
        pnl=pnl, pnl_pct=pnl_pct
    ).model_dump()


@router.get("", response_model=APIResponse)
async def get_trades(status: Optional[str] = Query(None, description="Filter trades by status"), db: Session = Depends(get_db)):
    """ Get all trades with optional filtering by status. """
    try:
        repo = TradeRepository(db)
        trade_status = TradeStatus(status) if status else None
        trades = repo.get_all_trades(status=trade_status)
        return APIResponse(success=True, message="Trades retrieved", data=[_build_response(t) for t in trades])
    except KeyError:
        return APIResponse(success=False, message=f"Invalid status: {status}")
    except Exception as exc:
        logger.error("Error fetching trades: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))
