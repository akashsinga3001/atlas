# backend/app/strategies/relative_leadership_v1/strategy.py

from app.strategies.base import Strategy
from app.strategies.context import StrategyContext
from app.strategies.observation import Observation
from app.strategies.relative_leadership_v1.logic import rank_universe, detect_transitions
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RelativeLeadershipV1Strategy(Strategy):
    code = "relative_leadership_v1"
    name = "Relative Leadership V1"

    def __init__(self):
        self._today_top10_tickers: list[str] = []

    def execute(self, context: StrategyContext) -> list[Observation]:
        config = context.config
        entry_percentile = config["signal"]["entry_percentile"]
        exit_percentile = config["exit"]["relative_leadership_deterioration"]["outside_percentile"]

        today_snapshot = context.feature_service.get_snapshot(context.as_of_date)
        if today_snapshot.empty:
            return []

        today_ranked = rank_universe(today_snapshot, entry_percentile, exit_percentile)
        self._today_top10_tickers = today_ranked.loc[today_ranked["is_top_10"], "ticker"].tolist()

        # "Yesterday's" top-10% membership comes from what the previous run actually recorded
        # (build_run_metrics, read back via context.previous_run_metrics) rather than recomputing
        # that day's ranking fresh — see logic.detect_transitions for why: mom_6_1 is position-based
        # (.shift(21)/.shift(126)), so a later feature regeneration can silently change what a past
        # date's ranking would compute to, making an already-held ticker look like a brand-new
        # transition again. An empty/missing record (first-ever run, or a run that predates this
        # field) falls back to "nothing was top 10 yesterday" — the same default detect_transitions
        # already used for an unseen ticker.
        prev_top10_tickers = set(context.previous_run_metrics.get("top_10_tickers", []))

        transitions = detect_transitions(today_ranked, prev_top10_tickers)
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

    def build_run_metrics(self) -> dict:
        return {"top_10_tickers": self._today_top10_tickers}
