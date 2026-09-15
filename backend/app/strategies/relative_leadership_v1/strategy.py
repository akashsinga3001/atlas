# backend/app/strategies/relative_leadership_v1/strategy.py

from datetime import timedelta

from app.strategies.base import Strategy
from app.strategies.context import StrategyContext
from app.strategies.observation import Observation
from app.strategies.relative_leadership_v1.logic import rank_universe, detect_transitions
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RelativeLeadershipV1Strategy(Strategy):
    code = "relative_leadership_v1"
    name = "Relative Leadership V1"

    def execute(self, context: StrategyContext) -> list[Observation]:
        config = context.config
        entry_percentile = config["signal"]["entry_percentile"]
        exit_percentile = config["exit"]["relative_leadership_deterioration"]["outside_percentile"]

        today_snapshot = context.feature_service.get_snapshot(context.as_of_date)
        if today_snapshot.empty:
            return []

        # The previous ELIGIBLE trading session, not calendar-yesterday — get_snapshot's cutoff
        # is a <= filter against actual OHLCV rows, so it naturally skips weekends/holidays.
        today_session_date = today_snapshot["candle_timestamp"].max()
        prev_snapshot = context.feature_service.get_snapshot(today_session_date - timedelta(days=1))

        today_ranked = rank_universe(today_snapshot, entry_percentile, exit_percentile)
        prev_ranked = rank_universe(prev_snapshot, entry_percentile, exit_percentile) if not prev_snapshot.empty else prev_snapshot

        transitions = detect_transitions(today_ranked, prev_ranked)
        logger.debug(f"{self.name}: {len(transitions)} new top-10% transitions at {context.as_of_date}")

        # Already-held securities are not filtered out here — TradeService.run_entry() already
        # skips any signal whose security has an open/pending trade. No pyramiding results either way.
        observations = []
        for row in transitions.itertuples():
            observations.append(Observation(
                security_id=row.security_id,
                observed_at=row.candle_timestamp,
                payload={"ticker": row.ticker, "strategy": self.code, "mom_6_1": row.mom_6_1, "rank": int(row.rank), "percentile_rank": row.percentile_rank},
            ))

        return observations
