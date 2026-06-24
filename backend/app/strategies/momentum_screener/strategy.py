# backend/app/strategies/momentum_screener/strategy.py

import pandas as pd

from app.strategies.base import Strategy
from app.strategies.context import StrategyContext
from app.strategies.observation import Observation


class MomentumScreenerStrategy(Strategy):
    code = "momentum_screener"
    name = "Momentum Screener"

    def execute(self, context: StrategyContext, ) -> list[Observation]:

        snapshot = context.feature_service.get_snapshot(context.as_of_date)
        if snapshot.empty:
            return []

        config = context.config
        thresholds = context.feature_service.get_global_quantiles(config["setup"]["quantiles"])
        signals = snapshot.copy()

        for feature, threshold in thresholds.items():
            signals = signals[signals[feature] >= threshold]

        selection_config = config["selection"]
        signals = signals.sort_values(by=selection_config["sort_by"], ascending=selection_config["ascending"], )
        signals = signals.head(selection_config["max_signals"])
        observations = []

        for row in signals.itertuples():
            observations.append(Observation(security_id=row.security_id, observed_at=row.candle_timestamp, payload={ "ticker": row.ticker, "strategy": self.code, "features": { feature: getattr(row, feature) for feature in config["setup"]["quantiles"] } }))

        return observations
