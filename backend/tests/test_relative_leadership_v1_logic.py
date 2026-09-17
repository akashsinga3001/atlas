# backend/tests/test_relative_leadership_v1_logic.py

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from app.enums.trade import ExitReason
from app.exit_evaluators.context import ExitEvaluatorContext
from app.exit_evaluators.relative_leadership_deterioration.evaluator import RelativeLeadershipDeteriorationEvaluator
from app.features.momentum import MomentumFeatures
from app.strategies.relative_leadership_v1.logic import detect_transitions, rank_universe


# --------------------------------------------------------------------------- #
#  Momentum (mom_6_1)                                                          #
# --------------------------------------------------------------------------- #

def _price_series(n: int) -> pd.DataFrame:
    """One ticker with n daily rows, close = 100, 101, 102, ... (deterministic, monotonic)."""
    return pd.DataFrame({"ticker": ["AAA"] * n, "candle_timestamp": pd.date_range("2020-01-01", periods=n, freq="D"), "close": [100.0 + i for i in range(n)]})


def test_momentum_6_1_correct_offsets():
    df = _price_series(200)
    result = MomentumFeatures.transform(df)
    row = result.iloc[-1]
    expected = (100.0 + 199 - 21) / (100.0 + 199 - 126) - 1
    assert row["mom_6_1"] == pytest.approx(expected)


def test_momentum_6_1_missing_history_is_null_not_zero():
    df = _price_series(100)  # fewer than 127 observations anywhere
    result = MomentumFeatures.transform(df)
    assert result["mom_6_1"].isna().all()


def test_momentum_6_1_becomes_valid_exactly_at_127_observations():
    df = _price_series(127)
    result = MomentumFeatures.transform(df)
    assert pd.notna(result.iloc[-1]["mom_6_1"])
    assert result.iloc[-2]["mom_6_1"] is None or pd.isna(result.iloc[-2]["mom_6_1"])


def test_momentum_6_1_does_not_fillna_zero():
    """Unlike ret_N, a security with insufficient history must not silently read as 0."""
    df = _price_series(50)
    result = MomentumFeatures.transform(df)
    assert result["mom_6_1"].isna().all()
    assert not (result["mom_6_1"] == 0).any()


# --------------------------------------------------------------------------- #
#  Cross-sectional ranking                                                     #
# --------------------------------------------------------------------------- #

def _snapshot(momentum_by_ticker: dict[str, float | None]) -> pd.DataFrame:
    tickers = sorted(momentum_by_ticker.keys())
    return pd.DataFrame({
        "security_id": list(range(1, len(tickers) + 1)),
        "ticker": tickers,
        "candle_timestamp": pd.Timestamp("2026-06-01"),
        "mom_6_1": [momentum_by_ticker[t] for t in tickers],
    })


def test_rank_universe_orders_strongest_first():
    snapshot = _snapshot({"A": 0.10, "B": 0.30, "C": 0.20})
    ranked = rank_universe(snapshot, entry_percentile=0.10, exit_percentile=0.30)
    assert list(ranked["ticker"]) == ["B", "C", "A"]
    assert list(ranked["rank"]) == [1, 2, 3]


def test_rank_universe_excludes_missing_momentum():
    snapshot = _snapshot({"A": 0.10, "B": None, "C": 0.20})
    ranked = rank_universe(snapshot, entry_percentile=0.10, exit_percentile=0.30)
    assert "B" not in set(ranked["ticker"])
    assert len(ranked) == 2


def test_rank_universe_boundaries_non_round_universe():
    # 97 securities: top 10% -> percentile_rank <= 0.10 -> rank <= 9.7 -> ranks 1..9 qualify (9 stocks).
    momentum = {f"T{i:03d}": float(97 - i) for i in range(97)}
    snapshot = _snapshot(momentum)
    ranked = rank_universe(snapshot, entry_percentile=0.10, exit_percentile=0.30)
    assert ranked["is_top_10"].sum() == 9
    # top 30% -> rank <= 29.1 -> ranks 1..29 qualify (29 stocks).
    assert ranked["is_top_30"].sum() == 29


def test_rank_universe_tie_break_is_ticker_ascending():
    snapshot = _snapshot({"B": 0.10, "A": 0.10, "C": 0.10})
    ranked = rank_universe(snapshot, entry_percentile=0.10, exit_percentile=0.30)
    assert list(ranked["ticker"]) == ["A", "B", "C"]


def test_rank_universe_negative_momentum_can_still_qualify():
    """Negative absolute momentum must not disqualify a security whose cross-sectional rank qualifies."""
    snapshot = _snapshot({"A": -0.40, "B": -0.50, "C": -0.60})
    ranked = rank_universe(snapshot, entry_percentile=0.34, exit_percentile=1.0)
    assert ranked.iloc[0]["ticker"] == "A"
    assert bool(ranked.iloc[0]["is_top_10"]) is True


# --------------------------------------------------------------------------- #
#  Transition signals                                                         #
# --------------------------------------------------------------------------- #

def _top10_tickers(ranked: pd.DataFrame) -> set:
    """Mirrors RelativeLeadershipV1Strategy.build_run_metrics()'s recorded top_10_tickers set —
    the frozen record a later run's prev_top10_tickers argument is sourced from, not a re-ranked
    previous-session DataFrame."""
    return set(ranked.loc[ranked["is_top_10"], "ticker"]) if not ranked.empty else set()


def test_transition_outside_to_inside_emits_signal():
    prev = rank_universe(_snapshot({"A": 0.05, "B": 0.50}), 0.50, 1.0)   # A outside top50%, B inside
    today = rank_universe(_snapshot({"A": 0.60, "B": 0.05}), 0.50, 1.0)  # A now inside, B now outside
    transitions = detect_transitions(today, _top10_tickers(prev))
    assert list(transitions["ticker"]) == ["A"]


def test_no_signal_when_remaining_inside():
    prev = rank_universe(_snapshot({"A": 0.60, "B": 0.05}), 0.50, 1.0)
    today = rank_universe(_snapshot({"A": 0.55, "B": 0.05}), 0.50, 1.0)
    transitions = detect_transitions(today, _top10_tickers(prev))
    assert transitions.empty


def test_no_entry_signal_for_inside_to_outside():
    prev = rank_universe(_snapshot({"A": 0.60, "B": 0.05}), 0.50, 1.0)
    today = rank_universe(_snapshot({"A": 0.05, "B": 0.60}), 0.50, 1.0)
    transitions = detect_transitions(today, _top10_tickers(prev))
    # Only B (newly inside) signals; A leaving does not produce an entry signal.
    assert list(transitions["ticker"]) == ["B"]


def test_repeated_outside_inside_outside_inside_can_signal_twice():
    # 4 securities so "top 50%" (rank <= 2) has room for A to move in and out of contention
    # without the fixed B/C/D pool itself being the thing under test.
    outside = {"A": 0.05, "B": 0.90, "C": 0.80, "D": 0.70}
    inside = {"A": 0.85, "B": 0.90, "C": 0.80, "D": 0.70}  # A ranks 2nd, ahead of C

    day1_prev = rank_universe(_snapshot(outside), 0.50, 1.0)
    day1_today = rank_universe(_snapshot(inside), 0.50, 1.0)
    assert "A" in set(detect_transitions(day1_today, _top10_tickers(day1_prev))["ticker"])

    day2_today = rank_universe(_snapshot(outside), 0.50, 1.0)
    assert "A" not in set(detect_transitions(day2_today, _top10_tickers(day1_today))["ticker"])  # A left — no entry signal for leaving

    day3_today = rank_universe(_snapshot(inside), 0.50, 1.0)
    assert "A" in set(detect_transitions(day3_today, _top10_tickers(day2_today))["ticker"])  # A re-enters — second signal


def test_transitions_sorted_momentum_desc_ticker_asc():
    prev = rank_universe(_snapshot({"A": 0.01, "B": 0.01, "C": 0.01}), 0.01, 1.0)
    today = rank_universe(_snapshot({"A": 0.20, "B": 0.30, "C": 0.20}), 1.0, 1.0)
    transitions = detect_transitions(today, _top10_tickers(prev))
    assert list(transitions["ticker"]) == ["B", "A", "C"]  # B strongest; A/C tie -> ticker asc


def test_detect_transitions_with_empty_previous_session():
    """No previous ranked session (e.g. very first run) — absence counts as 'not top 10 yesterday'."""
    today = rank_universe(_snapshot({"A": 0.50}), 1.0, 1.0)
    transitions = detect_transitions(today, set())
    assert list(transitions["ticker"]) == ["A"]


# --------------------------------------------------------------------------- #
#  Exit streak (RelativeLeadershipDeteriorationEvaluator)                      #
# --------------------------------------------------------------------------- #

def _make_trade(security_id: int, streak: int) -> SimpleNamespace:
    strategy_version = SimpleNamespace(config={"exit": {"relative_leadership_deterioration": {"confirmation_sessions": 3}}})
    return SimpleNamespace(security_id=security_id, state={"outside_top30_streak": streak}, strategy_version=strategy_version)


def _evaluate(evaluator: RelativeLeadershipDeteriorationEvaluator, trade: SimpleNamespace, outside_top_30: bool):
    context = ExitEvaluatorContext(trade=trade, as_of_date=pd.Timestamp("2026-06-01"), close_price=100.0, features={"outside_top_30_by_security": {trade.security_id: outside_top_30}})
    return evaluator.evaluate(context)


def test_exit_streak_out_out_out_exits_on_third_close():
    evaluator = RelativeLeadershipDeteriorationEvaluator()
    trade = _make_trade(security_id=1, streak=0)

    d1 = _evaluate(evaluator, trade, True)
    trade.state.update(d1.state_update)
    assert d1.should_exit is False

    d2 = _evaluate(evaluator, trade, True)
    trade.state.update(d2.state_update)
    assert d2.should_exit is False

    d3 = _evaluate(evaluator, trade, True)
    assert d3.should_exit is True
    assert d3.exit_reason == ExitReason.RELATIVE_LEADERSHIP_DETERIORATION


def test_exit_streak_out_out_in_resets_no_exit():
    evaluator = RelativeLeadershipDeteriorationEvaluator()
    trade = _make_trade(security_id=1, streak=0)

    for outside in (True, True, False):
        decision = _evaluate(evaluator, trade, outside)
        trade.state.update(decision.state_update)

    assert decision.should_exit is False
    assert trade.state["outside_top30_streak"] == 0


def test_exit_streak_out_in_out_final_streak_is_one():
    evaluator = RelativeLeadershipDeteriorationEvaluator()
    trade = _make_trade(security_id=1, streak=0)

    for outside in (True, False, True):
        decision = _evaluate(evaluator, trade, outside)
        trade.state.update(decision.state_update)

    assert decision.should_exit is False
    assert trade.state["outside_top30_streak"] == 1


def test_exit_streak_in_out_out_out_exits_on_final_close():
    evaluator = RelativeLeadershipDeteriorationEvaluator()
    trade = _make_trade(security_id=1, streak=0)

    decision = None
    for outside in (False, True, True, True):
        decision = _evaluate(evaluator, trade, outside)
        trade.state.update(decision.state_update)

    assert decision.should_exit is True


def test_security_removed_from_universe_defaults_to_outside_top_30():
    """A security absent from the day's ranked map (removed from the live universe) must be
    treated as outside top 30% — the approved policy for universe removal while held."""
    evaluator = RelativeLeadershipDeteriorationEvaluator()
    trade = _make_trade(security_id=1, streak=2)
    context = ExitEvaluatorContext(trade=trade, as_of_date=pd.Timestamp("2026-06-01"), close_price=100.0, features={"outside_top_30_by_security": {}})  # security_id 1 absent
    decision = evaluator.evaluate(context)
    assert decision.should_exit is True
    assert decision.state_update["outside_top30_streak"] == 3
