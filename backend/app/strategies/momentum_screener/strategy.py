# backend/app/strategies/momentum_screener/strategy.py

import pandas as pd

from app.strategies.base import Strategy
from app.strategies.context import StrategyContext
from app.strategies.observation import Observation


class MomentumScreenerStrategy(Strategy):
    code = "momentum_screener"
    name = "Momentum Screener"

    async def execute(self, context: StrategyContext) -> list[Observation]:
        """Execute the momentum screener strategy."""
        features = context.feature_service.get_snapshot(context.as_of_date)
        if features.empty:
            return []

        screened = self._screen(features)

        return [Observation(security_id=row.security_id, observed_at=row.candle_timestamp, payload={ "ticker": row.ticker, "opportunity_score": row.opportunity_score, "atr_pct": row.atr_pct, "base_tightness": row.base_tightness, "ema_compression": row.ema_compression, "close_near_high": row.close_near_high }) for row in screened.itertuples()]

    def _screen(self, features: pd.DataFrame) -> pd.DataFrame:
        """Screen the features to identify momentum opportunities."""
        features = features.copy()
        features["opportunity_score"] = 0.9 * features["atr_pct"].rank(pct=True) + 0.1 * features["base_tightness"].rank(pct=True)

        ema_threshold = features["ema_compression"].quantile(0.90)
        close_threshold = features["close_near_high"].quantile(0.80)

        screened = features[(features["ema_compression"] >= ema_threshold) & (features["close_near_high"] >= close_threshold)]
        screened = screened.sort_values("opportunity_score", ascending=False)
        return screened.head(10)
