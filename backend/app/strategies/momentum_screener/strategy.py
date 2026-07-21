# backend/app/strategies/momentum_screener/strategy.py

import pandas as pd

from app.strategies.base import Strategy
from app.strategies.context import StrategyContext
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
        signals = snapshot.copy()

        logger.debug(f"Applying thresholds: {thresholds}")

        for feature, threshold in thresholds.items():
            signals = signals[signals[feature] >= threshold]

        logger.debug(f"Filtered signals count after applying thresholds: {len(signals)}")

        selection_config = config["selection"]
        max_signals = selection_config["max_signals"]
        if selection_config["sort_by"] == "random":
            signals = signals.sample(n=min(max_signals, len(signals)))
        else:
            signals = signals.sort_values(by=selection_config["sort_by"], ascending=selection_config["ascending"])
            signals = signals.head(max_signals)
        observations = []

        for row in signals.itertuples():
            observations.append(Observation(security_id=row.security_id, observed_at=row.candle_timestamp, payload={ "ticker": row.ticker, "strategy": self.code, "features": { feature: getattr(row, feature) for feature in config["setup"]["quantiles"] } }))

        return observations
