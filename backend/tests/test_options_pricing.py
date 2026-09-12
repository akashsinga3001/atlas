# backend/tests/test_options_pricing.py

import pytest

from app.utils.options_pricing import bs_price, bs_delta, implied_volatility, estimate_delta


class TestBsPrice:
    def test_call_price_positive_for_reasonable_inputs(self):
        price = bs_price(spot=22000, strike=22200, dte_years=35 / 365, rate=0.065, vol=0.14, option_type="CE")
        assert price > 0

    def test_put_price_positive_for_reasonable_inputs(self):
        price = bs_price(spot=22000, strike=21800, dte_years=35 / 365, rate=0.065, vol=0.14, option_type="PE")
        assert price > 0

    def test_zero_dte_falls_back_to_intrinsic(self):
        assert bs_price(spot=22200, strike=22000, dte_years=0, rate=0.065, vol=0.14, option_type="CE") == 200
        assert bs_price(spot=21800, strike=22000, dte_years=0, rate=0.065, vol=0.14, option_type="PE") == 200
        assert bs_price(spot=22000, strike=22000, dte_years=0, rate=0.065, vol=0.14, option_type="CE") == 0

    def test_higher_vol_means_higher_price(self):
        low = bs_price(spot=22000, strike=22200, dte_years=35 / 365, rate=0.065, vol=0.10, option_type="CE")
        high = bs_price(spot=22000, strike=22200, dte_years=35 / 365, rate=0.065, vol=0.25, option_type="CE")
        assert high > low


class TestBsDelta:
    def test_atm_call_delta_near_half(self):
        delta = bs_delta(spot=22000, strike=22000, dte_years=35 / 365, rate=0.065, vol=0.14, option_type="CE")
        assert 0.4 < delta < 0.6

    def test_atm_put_delta_near_negative_half(self):
        delta = bs_delta(spot=22000, strike=22000, dte_years=35 / 365, rate=0.065, vol=0.14, option_type="PE")
        assert -0.6 < delta < -0.4

    def test_deep_otm_call_delta_near_zero(self):
        delta = bs_delta(spot=22000, strike=26000, dte_years=35 / 365, rate=0.065, vol=0.14, option_type="CE")
        assert delta < 0.05

    def test_deep_itm_call_delta_near_one(self):
        delta = bs_delta(spot=22000, strike=18000, dte_years=35 / 365, rate=0.065, vol=0.14, option_type="CE")
        assert delta > 0.95

    def test_put_delta_always_nonpositive(self):
        for strike in (18000, 20000, 22000, 24000, 26000):
            delta = bs_delta(spot=22000, strike=strike, dte_years=35 / 365, rate=0.065, vol=0.14, option_type="PE")
            assert delta <= 0

    def test_call_delta_always_nonnegative(self):
        for strike in (18000, 20000, 22000, 24000, 26000):
            delta = bs_delta(spot=22000, strike=strike, dte_years=35 / 365, rate=0.065, vol=0.14, option_type="CE")
            assert delta >= 0


class TestImpliedVolatility:
    def test_round_trips_a_known_price(self):
        true_vol = 0.16
        price = bs_price(spot=22000, strike=22200, dte_years=35 / 365, rate=0.065, vol=true_vol, option_type="CE")
        solved = implied_volatility(price, spot=22000, strike=22200, dte_years=35 / 365, rate=0.065, option_type="CE")
        assert solved == pytest.approx(true_vol, abs=1e-4)

    def test_put_round_trips_a_known_price(self):
        true_vol = 0.20
        price = bs_price(spot=22000, strike=21500, dte_years=35 / 365, rate=0.065, vol=true_vol, option_type="PE")
        solved = implied_volatility(price, spot=22000, strike=21500, dte_years=35 / 365, rate=0.065, option_type="PE")
        assert solved == pytest.approx(true_vol, abs=1e-4)

    def test_none_for_non_positive_price(self):
        assert implied_volatility(0, spot=22000, strike=22200, dte_years=35 / 365, rate=0.065, option_type="CE") is None
        assert implied_volatility(-5, spot=22000, strike=22200, dte_years=35 / 365, rate=0.065, option_type="CE") is None

    def test_none_for_zero_dte(self):
        assert implied_volatility(100, spot=22000, strike=22200, dte_years=0, rate=0.065, option_type="CE") is None

    def test_none_for_price_at_or_below_intrinsic(self):
        # Deep ITM call priced at exactly intrinsic has no time value for BS to explain.
        intrinsic = 2000
        assert implied_volatility(intrinsic, spot=22000, strike=20000, dte_years=35 / 365, rate=0.065, option_type="CE") is None


class TestEstimateDelta:
    def test_matches_bs_delta_for_the_same_solved_vol(self):
        true_vol = 0.15
        price = bs_price(spot=22000, strike=22300, dte_years=35 / 365, rate=0.065, vol=true_vol, option_type="CE")
        estimated = estimate_delta(price, spot=22000, strike=22300, dte_years=35 / 365, rate=0.065, option_type="CE")
        expected = bs_delta(spot=22000, strike=22300, dte_years=35 / 365, rate=0.065, vol=true_vol, option_type="CE")
        assert estimated == pytest.approx(expected, abs=1e-3)

    def test_none_when_iv_unsolvable(self):
        assert estimate_delta(0, spot=22000, strike=22300, dte_years=35 / 365, rate=0.065, option_type="CE") is None
