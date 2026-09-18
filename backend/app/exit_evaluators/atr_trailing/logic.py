# backend/app/exit_evaluators/atr_trailing/logic.py

from typing import Optional


def compute_atr_trailing_stop(close: float, atr_14: Optional[float], atr_multiplier: float, highest_close: Optional[float], current_stop: Optional[float]) -> dict:
    """Pure ATR trailing-stop ratchet — the single source of truth for this math, shared by the
    live exit evaluator, the initial-stop calculation at entry, and the "what would this missed
    signal have done" performance simulation (previously three independent copies; see CLAUDE.md's
    strategy-logic convention on why this class of capital-gating math belongs in one pure
    function). Tracks the highest close seen so far, derives a candidate stop from it, never lowers
    an existing stop, and reports whether today's close breaches it.

    Returns {"highest_close", "current_stop", "should_exit"}. If atr_14 isn't available yet,
    highest_close still ratchets but current_stop/should_exit are left unchanged/False — it's up
    to the caller to decide what that means for it (skip today's evaluation, no stop yet, etc.).
    """
    if highest_close is None or close > highest_close:
        highest_close = close

    if atr_14 is None:
        return {"highest_close": highest_close, "current_stop": current_stop, "should_exit": False}

    new_stop = highest_close - (atr_multiplier * float(atr_14))
    if current_stop is None or new_stop > current_stop:
        current_stop = new_stop

    return {"highest_close": highest_close, "current_stop": current_stop, "should_exit": close <= current_stop}
