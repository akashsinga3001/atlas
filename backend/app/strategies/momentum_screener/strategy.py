# backend/app/strategies/momentum_screener/strategy.py

import pandas as pd

from app.strategies.base import Strategy
from app.strategies.context import StrategyContext
from app.strategies.momentum_screener.logic import select_signals
from app.strategies.observation import Observation
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MomentumScreenerStrategy(Strategy):
    code = "momentum_screener"
    name = "Momentum Screener"

    def execute(self, context: StrategyContext) -> list[Observation]:

        snapshot = context.feature_service.get_snapshot(context.as_of_date)
        if snapshot.empty:
            return []

        logger.debug(f"Executing {self.name} strategy for {len(snapshot)} securities at {context.as_of_date}")

        config = context.config
        thresholds = context.feature_service.get_global_quantiles(config["setup"]["quantiles"])
        logger.debug(f"Applying thresholds: {thresholds}")

        signals = select_signals(snapshot, thresholds, config["selection"])
        logger.debug(f"Filtered signals count after applying thresholds: {len(signals)}")

        observations = []

        for row in signals.itertuples():
            observations.append(Observation(security_id=row.security_id, observed_at=row.candle_timestamp, payload={ "ticker": row.ticker, "strategy": self.code, "features": { feature: getattr(row, feature) for feature in config["setup"]["quantiles"] } }))

        return observations
