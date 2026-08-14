# backend/app/strategies/nifty_iron_condor/strategy.py

from datetime import datetime

from app.strategies.base import Strategy
from app.strategies.context import StrategyContext
from app.strategies.observation import Observation
from app.repositories.security import SecurityRepository
from app.services.brokers.kite import KiteService
from app.utils.trading_calendar import is_nse_trading_day
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NiftyIronCondorSignalStrategy(Strategy):
    """Monday signal for the NIFTY iron condor: records that day's NIFTY 50 close as spot_close.

    No conditional logic — the strategy is unconditional by design (every NSE-trading Monday
    is a signal). Actual order entry happens the next NSE trading day; see OptionsTradeService.
    """
    code = "nifty_iron_condor"
    name = "NIFTY Iron Condor"

    def execute(self, context: StrategyContext) -> list[Observation]:
        as_of_date = context.as_of_date.date()
        config = context.config

        signal_weekday = config.get("signal_day_of_week", 0)
        if as_of_date.weekday() != signal_weekday or not is_nse_trading_day(as_of_date):
            logger.debug(f"{as_of_date} is not a signal day for {self.code} (weekday={as_of_date.weekday()}) — no signal.")
            return []

        db = context.feature_service.db
        security_repo = SecurityRepository(db)
        underlying_ticker = config.get("underlying_ticker", "NIFTY 50")
        security = security_repo.get_by_ticker_exchange(underlying_ticker, "NSE")

        if not security:
            logger.error(f"Underlying security '{underlying_ticker}' not found in securities table — cannot generate signal.")
            return []

        kite_service = KiteService()
        kite_ticker = f"NSE:{underlying_ticker}"

        try:
            quote = kite_service.get_quotes([kite_ticker])
            spot_close = quote[kite_ticker]["last_price"]
        except Exception:
            logger.error(f"Failed to fetch spot quote for {underlying_ticker} — no signal.", exc_info=True)
            return []

        logger.info(f"NIFTY iron condor signal for {as_of_date}: spot_close={spot_close}")

        return [Observation(security_id=security.id, observed_at=datetime.combine(as_of_date, datetime.min.time()), payload={ "spot_close": spot_close, "strategy": self.code })]
