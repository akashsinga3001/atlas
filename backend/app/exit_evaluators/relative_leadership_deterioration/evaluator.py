# backend/app/exit_evaluators/relative_leadership_deterioration/evaluator.py

from app.enums.trade import ExitReason
from app.exit_evaluators.base import ExitEvaluator
from app.exit_evaluators.context import ExitEvaluatorContext
from app.exit_evaluators.decision import ExitDecision
from app.strategies.relative_leadership_v1.logic import rank_universe
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RelativeLeadershipDeteriorationEvaluator(ExitEvaluator):
    """Exit evaluator for relative_leadership_v1's frozen 3-session leadership-deterioration rule."""
    code = "relative_leadership_deterioration"

    def prepare_run_context(self, feature_service, as_of_date) -> dict:
        """Rank the whole universe once per run — "is this ticker outside the top 30% today"
        is a cross-sectional property, not something a single trade's own features can answer.

        A security absent from the map (removed from the live universe, or no valid mom_6_1)
        defaults to "outside top 30%" wherever it's looked up in evaluate() below — this is the
        deliberate policy for a security dropped from the universe while held: it simply can
        never rank inside the top 30% again, so it exits via the ordinary 3-session streak
        rather than a separate forced-exit path.
        """
        snapshot = feature_service.get_snapshot(as_of_date)
        if snapshot.empty:
            return {"outside_top_30_by_security": {}}

        ranked = rank_universe(snapshot, entry_percentile=1.0, exit_percentile=0.30)
        outside_top_30_by_security = {int(row.security_id): not bool(row.is_top_30) for row in ranked.itertuples()}
        return {"outside_top_30_by_security": outside_top_30_by_security}

    def evaluate(self, context: ExitEvaluatorContext) -> ExitDecision:
        trade = context.trade
        config = trade.strategy_version.config.get("exit", {}).get("relative_leadership_deterioration", {})
        confirmation_sessions = config.get("confirmation_sessions", 3)

        outside_map = context.features.get("outside_top_30_by_security", {})
        is_outside_top_30 = outside_map.get(trade.security_id, True)

        streak = trade.state.get("outside_top30_streak", 0)
        new_streak = streak + 1 if is_outside_top_30 else 0

        should_exit = new_streak >= confirmation_sessions

        return ExitDecision(
            should_exit=should_exit,
            exit_reason=ExitReason.RELATIVE_LEADERSHIP_DETERIORATION if should_exit else None,
            state_update={"outside_top30_streak": new_streak},
            snapshot_state={"outside_top_30": is_outside_top_30, "outside_top30_streak": new_streak},
        )
