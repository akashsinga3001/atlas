# backend/app/api/v1/portfolio.py

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AtlasException, InternalError
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
        # Timezone-aware, so a JS client's `new Date(...)` parses it as UTC rather than
        # misreading a naive timestamp as browser-local time (a 5.5h error for an IST viewer).
        data["computed_at"] = datetime.now(timezone.utc).isoformat()
        return APIResponse(success=True, message="Live account value retrieved", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception("Error fetching live account value: {}", exc)
        raise InternalError(message=str(exc)) from exc


@router.get("/sector-exposure", response_model=APIResponse)
async def get_sector_exposure(db: Session = Depends(get_db)):
    """Return live open-position exposure by sector, and single-position/sector concentration."""
    try:
        data = FundService(db, KiteService()).get_sector_exposure()
        return APIResponse(success=True, message="Sector exposure retrieved", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception("Error fetching sector exposure: {}", exc)
        raise InternalError(message=str(exc)) from exc


@router.get("/today-pnl", response_model=APIResponse)
async def get_today_pnl_summary(db: Session = Depends(get_db)):
    """Return today's P&L split into realized (closed today) vs. unrealized (live mark)."""
    try:
        data = PortfolioService(db, KiteService()).get_today_pnl_summary()
        return APIResponse(success=True, message="Today's P&L retrieved", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception("Error fetching today's P&L: {}", exc)
        raise InternalError(message=str(exc)) from exc


@router.get("/strategy-performance", response_model=APIResponse)
async def get_strategy_performance(db: Session = Depends(get_db)):
    """Return per-active-strategy open-position count, realized P&L, and return %."""
    try:
        data = PortfolioService(db).get_strategy_performance()
        return APIResponse(success=True, message="Strategy performance retrieved", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception("Error fetching strategy performance: {}", exc)
        raise InternalError(message=str(exc)) from exc


@router.get("/stats", response_model=APIResponse)
async def get_portfolio_stats(db: Session = Depends(get_db)):
    """Return aggregate performance statistics across all trades."""
    try:
        stats = PortfolioService(db).get_stats()
        return APIResponse(success=True, message="Stats retrieved", data=stats)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception("Error fetching portfolio stats: {}", exc)
        raise InternalError(message=str(exc)) from exc


@router.get("/equity-curve", response_model=APIResponse)
async def get_equity_curve(db: Session = Depends(get_db)):
    """Return time-ordered cumulative P&L data points for the equity curve chart."""
    try:
        points = PortfolioService(db).get_equity_curve()
        return APIResponse(success=True, message="Equity curve retrieved", data=points)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception("Error fetching equity curve: {}", exc)
        raise InternalError(message=str(exc)) from exc


@router.get("/nav-curve", response_model=APIResponse)
async def get_nav_curve(db: Session = Depends(get_db)):
    """Return time-ordered daily account value (cash + holdings) snapshots with cash flow markers."""
    try:
        points = PortfolioService(db).get_nav_curve()
        return APIResponse(success=True, message="NAV curve retrieved", data=points)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception("Error fetching NAV curve: {}", exc)
        raise InternalError(message=str(exc)) from exc


@router.get("/capital-allocation", response_model=APIResponse)
async def get_capital_allocation(db: Session = Depends(get_db)):
    """Return live account size and how it's split across active strategies, flagging overallocation."""
    try:
        account_size = FundService(db, KiteService()).compute_live_account_value()["total_value"]
        data = PortfolioService(db).get_capital_allocation(account_size)
        return APIResponse(success=True, message="Capital allocation retrieved", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception("Error fetching capital allocation: {}", exc)
        raise InternalError(message=str(exc)) from exc


@router.get("/analytics", response_model=APIResponse)
async def get_portfolio_analytics(db: Session = Depends(get_db)):
    """Return return distribution and sector performance analytics."""
    try:
        data = PortfolioService(db).get_analytics()
        return APIResponse(success=True, message="Analytics retrieved", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception("Error fetching portfolio analytics: {}", exc)
        raise InternalError(message=str(exc)) from exc
