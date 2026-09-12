# backend/tests/test_iron_condor_logic.py

from datetime import date

from app.enums.options import OptionsExitReason
from app.execution_engines.options_iron_condor.logic import (
    select_nearest_dte_expiry, select_delta_target_strike, compute_wing_strike,
    compute_spread_value, compute_max_loss_per_lot, compute_position_size, evaluate_exit_reason,
)


class TestSelectNearestDteExpiry:
    def test_picks_closest_to_target(self):
        as_of = date(2026, 1, 1)
        expiries = [date(2026, 1, 8), date(2026, 2, 5), date(2026, 3, 5)]  # DTE 7, 35, 63
        assert select_nearest_dte_expiry(expiries, as_of, target_dte=35) == date(2026, 2, 5)

    def test_empty_list_returns_none(self):
        assert select_nearest_dte_expiry([], date(2026, 1, 1), target_dte=35) is None

    def test_ties_break_to_first_min(self):
        as_of = date(2026, 1, 1)
        # DTE 30 and 40 are equidistant from 35
        expiries = [date(2026, 1, 31), date(2026, 2, 10)]
        assert select_nearest_dte_expiry(expiries, as_of, target_dte=35) in expiries


class TestSelectDeltaTargetStrike:
    def test_picks_nearest_within_tolerance(self):
        candidates = [(22000, 0.35), (22200, 0.24), (22300, 0.19), (22400, 0.12)]
        assert select_delta_target_strike(candidates, target_delta=0.20, tolerance=0.05) == 22300

    def test_none_when_nothing_within_tolerance(self):
        candidates = [(22000, 0.60), (22400, 0.05)]
        assert select_delta_target_strike(candidates, target_delta=0.20, tolerance=0.05) is None

    def test_empty_candidates_returns_none(self):
        assert select_delta_target_strike([], target_delta=0.20, tolerance=0.05) is None

    def test_exact_match_wins(self):
        candidates = [(22100, 0.22), (22200, 0.20), (22300, 0.17)]
        assert select_delta_target_strike(candidates, target_delta=0.20, tolerance=0.05) == 22200


class TestComputeWingStrike:
    def test_call_wing_is_above(self):
        assert compute_wing_strike(22200, 400, "CE") == 22600

    def test_put_wing_is_below(self):
        assert compute_wing_strike(21800, 400, "PE") == 21400


class TestComputeSpreadValue:
    def test_net_credit_shape(self):
        # short_call + short_put - long_call - long_put
        assert compute_spread_value(80, 75, 20, 18) == 117

    def test_can_be_negative_net_debit(self):
        assert compute_spread_value(10, 10, 30, 30) == -40


class TestComputeMaxLossPerLot:
    def test_wing_width_minus_credit_times_lot_size(self):
        assert compute_max_loss_per_lot(wing_width_points=400, net_credit_per_lot=117, lot_size=50) == (400 - 117) * 50

    def test_credit_larger_than_wing_gives_non_positive(self):
        assert compute_max_loss_per_lot(wing_width_points=400, net_credit_per_lot=500, lot_size=50) < 0


class TestComputePositionSize:
    """Sizing goes purely by capital / real broker margin per lot — no risk-fraction cap; only
    max_lots bounds it regardless of what the capital math alone allows."""

    def test_floors_never_rounds_up(self):
        # 100000 / 18000 -> 5.55 -> floors to 5, never rounds up to 6
        assert compute_position_size(capital=100_000, margin_per_lot=18_000, max_lots=50) == 5
        # exact multiple -> exactly 4 lots, no off-by-one
        assert compute_position_size(capital=100_000, margin_per_lot=25_000, max_lots=50) == 4

    def test_hard_capped_at_max_lots_regardless_of_capital_math(self):
        assert compute_position_size(capital=100_000_000, margin_per_lot=100, max_lots=50) == 50

    def test_zero_when_capital_smaller_than_one_lots_margin(self):
        assert compute_position_size(capital=10_000, margin_per_lot=18_000, max_lots=50) == 0

    def test_zero_for_non_positive_margin_per_lot(self):
        assert compute_position_size(capital=100_000, margin_per_lot=0, max_lots=50) == 0
        assert compute_position_size(capital=100_000, margin_per_lot=-10, max_lots=50) == 0

    def test_zero_for_non_positive_capital(self):
        assert compute_position_size(capital=0, margin_per_lot=18_000, max_lots=50) == 0


class TestEvaluateExitReason:
    """The exact priority-ordered exit chain, including the credit-reconciliation guard against
    the specific bug the spec calls out: a stale decision-time credit must never be used."""

    DEFAULTS = dict(time_exit_dte=7, profit_target_pct=0.5, stop_loss_multiple=2.0)

    def test_expiry_safety_exit_wins_over_everything(self):
        reason = evaluate_exit_reason(days_to_expiry=0, real_entry_credit=100, cost_to_close=50, **self.DEFAULTS)
        assert reason == OptionsExitReason.EXPIRY_EXIT

    def test_expiry_safety_exit_for_negative_days(self):
        reason = evaluate_exit_reason(days_to_expiry=-1, real_entry_credit=100, cost_to_close=1, **self.DEFAULTS)
        assert reason == OptionsExitReason.EXPIRY_EXIT

    def test_time_exit_fires_regardless_of_pnl(self):
        # cost_to_close=1000 would otherwise be a stop-loss disaster, but time exit still wins
        reason = evaluate_exit_reason(days_to_expiry=7, real_entry_credit=100, cost_to_close=1000, **self.DEFAULTS)
        assert reason == OptionsExitReason.TIME_EXIT

    def test_time_exit_boundary_is_inclusive(self):
        # cost_to_close=70 deliberately sits strictly between the profit-target (<=50) and
        # stop-loss (>=200) thresholds, so day 8 isolates "no exit" rather than coincidentally
        # also satisfying a P&L-based exit.
        assert evaluate_exit_reason(days_to_expiry=7, real_entry_credit=100, cost_to_close=70, **self.DEFAULTS) == OptionsExitReason.TIME_EXIT
        assert evaluate_exit_reason(days_to_expiry=8, real_entry_credit=100, cost_to_close=70, **self.DEFAULTS) is None

    def test_credit_reconciliation_guard_fires_before_profit_or_stop(self):
        # real_entry_credit <= 0 (net debit fill) must close immediately, never be treated as a
        # "100% profit" or divide-by-non-positive ratio.
        reason = evaluate_exit_reason(days_to_expiry=20, real_entry_credit=-5, cost_to_close=1, **self.DEFAULTS)
        assert reason == OptionsExitReason.CREDIT_RECONCILIATION

    def test_credit_reconciliation_guard_fires_for_exactly_zero_credit(self):
        reason = evaluate_exit_reason(days_to_expiry=20, real_entry_credit=0, cost_to_close=1, **self.DEFAULTS)
        assert reason == OptionsExitReason.CREDIT_RECONCILIATION

    def test_profit_target(self):
        # cost_to_close <= 50% of real_entry_credit
        reason = evaluate_exit_reason(days_to_expiry=20, real_entry_credit=100, cost_to_close=50, **self.DEFAULTS)
        assert reason == OptionsExitReason.PROFIT_TARGET

    def test_no_exit_just_above_profit_target(self):
        reason = evaluate_exit_reason(days_to_expiry=20, real_entry_credit=100, cost_to_close=50.01, **self.DEFAULTS)
        assert reason is None

    def test_stop_loss(self):
        # cost_to_close >= 2.0x real_entry_credit
        reason = evaluate_exit_reason(days_to_expiry=20, real_entry_credit=100, cost_to_close=200, **self.DEFAULTS)
        assert reason == OptionsExitReason.STOP_LOSS

    def test_no_exit_just_below_stop_loss(self):
        reason = evaluate_exit_reason(days_to_expiry=20, real_entry_credit=100, cost_to_close=199.99, **self.DEFAULTS)
        assert reason is None

    def test_holds_when_nothing_qualifies(self):
        reason = evaluate_exit_reason(days_to_expiry=20, real_entry_credit=100, cost_to_close=100, **self.DEFAULTS)
        assert reason is None

    def test_holds_when_real_entry_credit_not_yet_available(self):
        # Days-to-expiry checks pass, but fills aren't in yet — must not exit on missing data.
        reason = evaluate_exit_reason(days_to_expiry=20, real_entry_credit=None, cost_to_close=None, **self.DEFAULTS)
        assert reason is None

    def test_holds_when_cost_to_close_not_yet_available(self):
        reason = evaluate_exit_reason(days_to_expiry=20, real_entry_credit=100, cost_to_close=None, **self.DEFAULTS)
        assert reason is None

    def test_bug_scenario_from_spec_stale_credit_would_have_inverted_stop_loss(self):
        """The exact regression the spec warns about: a losing position whose actual fill was a
        net debit must trigger CREDIT_RECONCILIATION, never be evaluated as if a stale positive
        decision-time credit still applied (which could otherwise read a large cost_to_close as
        a small "% of credit" and falsely suppress the stop loss, or worse, register as a profit)."""
        # Actual fills came in as a net debit (-10), even though a decision-time quote might have
        # suggested a credit. cost_to_close is a large loss (900). With the guard, this must be
        # CREDIT_RECONCILIATION, not a profit/stop ratio computed against a stale positive number.
        reason = evaluate_exit_reason(days_to_expiry=20, real_entry_credit=-10, cost_to_close=900, **self.DEFAULTS)
        assert reason == OptionsExitReason.CREDIT_RECONCILIATION
