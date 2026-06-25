# backend/app/jobs/trade_entry.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.strategy import StrategyVersion, StrategySignal
from app.repositories.trade import TradeRepository
from app.services.brokers.kite import KiteService
from app.services.trade import TradeService
from app.services.portfolio import PortfolioService
from app.enums.trade import TradeStatus
from app.celery.tasks import TradeEntryTask
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.trade_entry.run_trade_entry", bind=True, base=TradeEntryTask)
def run_trade_entry(self, strategy_version_id: int) -> dict:
    """Evaluate signals and open new trades up to available slot count."""
    db = SessionLocal()
    try:
        strategy_version = db.query(StrategyVersion).filter(StrategyVersion.id == strategy_version_id).first()
        if not strategy_version:
            raise ValueError(f"StrategyVersion {strategy_version_id} not found")

        kite_service = KiteService()
        trade_service = TradeService(db, kite_service)
        portfolio_service = PortfolioService(db, kite_service)

        available_slots = portfolio_service.get_available_slots(strategy_version)
        if available_slots < 1:
            logger.info(f"No available slots for strategy version {strategy_version_id}. Skipping entry.")
            return { "success": True, "message": "NO_SLOTS_AVAILABLE", "data": { "trades_opened": 0 } }

        latest_run = strategy_version.runs[-1] if strategy_version.runs else None
        if not latest_run or not latest_run.signals:
            logger.info(f"No signals found for strategy version {strategy_version_id}. Skipping entry.")
            return { "success": True, "message": "NO_SIGNALS", "data": { "trades_opened": 0 } }

        trade_repo = TradeRepository(db)
        signals: list[StrategySignal] = sorted(latest_run.signals, key=lambda s: s.security.ticker)

        trades_opened = 0
        entry_date = date.today()

        for signal in signals:
            if trades_opened >= available_slots:
                break

            existing = trade_repo.get_by_security_and_status(signal.security_id, TradeStatus.OPEN)
            pending = trade_repo.get_by_security_and_status(signal.security_id, TradeStatus.PENDING)
            if existing or pending:
                logger.info(f"Skipping {signal.security.ticker} — already have an open/pending trade")
                continue

            trade = trade_service.open_trade(signal=signal, strategy_version=strategy_version, entry_date=entry_date)
            if trade:
                trades_opened += 1

        logger.info(f"Trade entry completed. Opened {trades_opened} trade(s) for version {strategy_version_id}.")
        return { "success": True, "message": "TRADE_ENTRY_COMPLETED", "data": { "trades_opened": trades_opened } }
    except Exception as e:
        logger.error(f"Trade entry failed for version {strategy_version_id}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
