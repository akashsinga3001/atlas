# backend/tests/test_nifty_iron_condor_strategy.py

import pytest

from app.strategies.nifty_iron_condor.strategy import compute_vix_percentile, compute_risk_flags


class TestComputeVixPercentile:
    def test_none_below_lookback_history(self):
        assert compute_vix_percentile(history_closes=[10.0] * 251, current_value=15.0, lookback_days=252) is None

    def test_none_for_empty_history(self):
        assert compute_vix_percentile(history_closes=[], current_value=15.0, lookback_days=252) is None

    def test_current_value_is_max_gives_100th_percentile(self):
        history = [float(v) for v in range(1, 253)]  # 1..252
        percentile = compute_vix_percentile(history_closes=history, current_value=252.0, lookback_days=252)
        assert percentile == 100.0

    def test_current_value_is_min_gives_near_zero_percentile(self):
        history = [float(v) for v in range(1, 253)]  # 1..252
        percentile = compute_vix_percentile(history_closes=history, current_value=1.0, lookback_days=252)
        # window = history (252 values) + [1.0] -> 2 of the 253 values are <= 1.0
        assert percentile == pytest.approx(2 / 253 * 100)

    def test_only_uses_the_trailing_window_not_older_history(self):
        # An outlier far outside the lookback window must not affect the percentile.
        history = [1000.0] + [10.0] * 252  # 253 values total, lookback=252 drops the outlier
        percentile = compute_vix_percentile(history_closes=history, current_value=10.0, lookback_days=252)
        assert percentile == 100.0  # window is 252x10.0 + current 10.0 -> all <= current


class TestComputeRiskFlags:
    def test_all_none_with_insufficient_history(self):
        flags = compute_risk_flags(nifty_closes=[100.0, 101.0], vix_closes=[12.0, 13.0], vix_percentile=50.0)
        assert flags == {"momentum_20d_negative": None, "worst_regime": None, "vol_expansion": None, "tail_event_recent": None}

    def test_momentum_negative_detected(self):
        nifty_closes = [100.0] * 21 + [90.0]  # 22 values; last vs value 20 days back is -10%
        flags = compute_risk_flags(nifty_closes=nifty_closes, vix_closes=[12.0] * 22, vix_percentile=50.0)
        assert flags["momentum_20d_negative"] is True

    def test_momentum_positive_detected(self):
        nifty_closes = [100.0] * 21 + [110.0]
        flags = compute_risk_flags(nifty_closes=nifty_closes, vix_closes=[12.0] * 22, vix_percentile=50.0)
        assert flags["momentum_20d_negative"] is False

    def test_worst_regime_requires_both_negative_momentum_and_high_vix_percentile(self):
        nifty_closes = [100.0] * 21 + [90.0]  # negative momentum

        low_vix = compute_risk_flags(nifty_closes=nifty_closes, vix_closes=[12.0] * 22, vix_percentile=50.0)
        assert low_vix["worst_regime"] is False

        high_vix = compute_risk_flags(nifty_closes=nifty_closes, vix_closes=[12.0] * 22, vix_percentile=70.0)
        assert high_vix["worst_regime"] is True

    def test_worst_regime_false_when_momentum_positive_even_with_high_vix(self):
        nifty_closes = [100.0] * 21 + [110.0]  # positive momentum
        flags = compute_risk_flags(nifty_closes=nifty_closes, vix_closes=[12.0] * 22, vix_percentile=90.0)
        assert flags["worst_regime"] is False

    def test_tail_event_recent_detected(self):
        # 11 closes, most recent day-over-day return is a -5% single-day move
        nifty_closes = [100.0] * 10 + [95.0]
        flags = compute_risk_flags(nifty_closes=nifty_closes, vix_closes=[12.0] * 11, vix_percentile=50.0)
        assert flags["tail_event_recent"] is True

    def test_tail_event_recent_false_without_a_big_move(self):
        nifty_closes = [100.0] * 10 + [99.5]  # -0.5%, not a tail event
        flags = compute_risk_flags(nifty_closes=nifty_closes, vix_closes=[12.0] * 11, vix_percentile=50.0)
        assert flags["tail_event_recent"] is False

    def test_tail_event_outside_lookback_window_not_flagged(self):
        # The big drop happened, but it's now further back than the 10-day lookback window.
        nifty_closes = [100.0, 95.0] + [95.0] * 10  # drop at index 1, then 10 flat days after
        flags = compute_risk_flags(nifty_closes=nifty_closes, vix_closes=[12.0] * 12, vix_percentile=50.0)
        assert flags["tail_event_recent"] is False
