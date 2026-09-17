# backend/app/api/v1/portfolio.py

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.brokers.kite import KiteService
from app.services.fund import FundService
from app.services.portfolio import PortfolioService
from app.schemas.base import APIResponse
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/live", response_model=APIResponse)
async def get_live_account_value(db: Session = Depends(get_db)):
    """Return live cash + mark-to-market holdings, computed fresh (not the once-daily snapshot)."""
    try:
        data = FundService(db, KiteService()).compute_live_account_value()
        data["computed_at"] = datetime.utcnow().isoformat()
        return APIResponse(success=True, message="Live account value retrieved", data=data)
    except Exception as exc:
        logger.error("Error fetching live account value: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))


@router.get("/stats", response_model=APIResponse)
async def get_portfolio_stats(db: Session = Depends(get_db)):
    """Return aggregate performance statistics across all trades."""
    try:
        stats = PortfolioService(db).get_stats()
        return APIResponse(success=True, message="Stats retrieved", data=stats)
    except Exception as exc:
        logger.error("Error fetching portfolio stats: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))


@router.get("/equity-curve", response_model=APIResponse)
async def get_equity_curve(db: Session = Depends(get_db)):
    """Return time-ordered cumulative P&L data points for the equity curve chart."""
    try:
        points = PortfolioService(db).get_equity_curve()
        return APIResponse(success=True, message="Equity curve retrieved", data=points)
    except Exception as exc:
        logger.error("Error fetching equity curve: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))


@router.get("/nav-curve", response_model=APIResponse)
async def get_nav_curve(db: Session = Depends(get_db)):
    """Return time-ordered daily account value (cash + holdings) snapshots with cash flow markers."""
    try:
        points = PortfolioService(db).get_nav_curve()
        return APIResponse(success=True, message="NAV curve retrieved", data=points)
    except Exception as exc:
        logger.error("Error fetching NAV curve: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))


@router.get("/capital-allocation", response_model=APIResponse)
async def get_capital_allocation(db: Session = Depends(get_db)):
    """Return account size and how it's split across active strategies, flagging overallocation."""
    try:
        data = PortfolioService(db).get_capital_allocation()
        return APIResponse(success=True, message="Capital allocation retrieved", data=data)
    except Exception as exc:
        logger.error("Error fetching capital allocation: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))


@router.get("/analytics", response_model=APIResponse)
async def get_portfolio_analytics(db: Session = Depends(get_db)):
    """Return return distribution and sector performance analytics."""
    try:
        data = PortfolioService(db).get_analytics()
        return APIResponse(success=True, message="Analytics retrieved", data=data)
    except Exception as exc:
        logger.error("Error fetching portfolio analytics: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))
