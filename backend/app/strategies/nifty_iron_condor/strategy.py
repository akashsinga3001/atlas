# backend/app/strategies/nifty_iron_condor/strategy.py

from datetime import datetime

from app.strategies.base import Strategy
from app.strategies.context import StrategyContext
from app.strategies.observation import Observation
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

        underlying_ticker = config.get("underlying_ticker", "NIFTY 50")
        security = context.feature_service.get_security_by_ticker(underlying_ticker, "NSE")

        if not security:
            logger.error(f"Underlying security '{underlying_ticker}' not found in securities table — cannot generate signal.")
            return []

        try:
            spot_close = context.quote_service_factory().get_last_price(underlying_ticker, "NSE")
        except Exception:
            logger.error(f"Failed to fetch spot quote for {underlying_ticker} — no signal.", exc_info=True)
            return []

        if not spot_close or spot_close <= 0:
            logger.error(f"No live price returned for {underlying_ticker} — no signal.")
            return []

        logger.info(f"NIFTY iron condor signal for {as_of_date}: spot_close={spot_close}")

        return [Observation(security_id=security.id, observed_at=datetime.combine(as_of_date, datetime.min.time()), payload={ "spot_close": spot_close, "strategy": self.code })]
