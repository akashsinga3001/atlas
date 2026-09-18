# backend/app/exit_evaluators/atr_trailing/evaluator.py

from app.enums.trade import ExitReason
from app.exit_evaluators.atr_trailing.logic import compute_atr_trailing_stop
from app.exit_evaluators.base import ExitEvaluator
from app.exit_evaluators.context import ExitEvaluatorContext
from app.exit_evaluators.decision import ExitDecision
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ATRTrailingStopEvaluator(ExitEvaluator):
    """Exit evaluator implementing the Average True Range (ATR) trailing stop strategy."""
    code = "atr_trailing_stop"

    def evaluate(self, context: ExitEvaluatorContext) -> ExitDecision:
        trade = context.trade
        close = context.close_price
        config = trade.strategy_version.config

        atr_multiplier = config.get("exit", {}).get("atr_trailing_stop", {}).get("atr_multiple", 5.0)
        atr_14 = context.features.get("atr_14")

        if atr_14 is None:
            logger.warning(f"atr_14 not available for trade {trade.id} — skipping exit evaluation")
            return ExitDecision(should_exit=False)

        result = compute_atr_trailing_stop(close=close, atr_14=atr_14, atr_multiplier=atr_multiplier, highest_close=trade.state.get("highest_close", close), current_stop=trade.state.get("current_stop"))
        should_exit = result["should_exit"]

        return ExitDecision(should_exit=should_exit, exit_reason=ExitReason.ATR_STOP if should_exit else None, state_update={ "highest_close": result["highest_close"], "current_stop": result["current_stop"], }, snapshot_state={ "atr_14": float(atr_14), "highest_close": result["highest_close"], "stop_price": result["current_stop"], }, )
