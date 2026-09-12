# backend/app/utils/options_pricing.py
#
# Black-Scholes option pricing/IV/delta math. Kite Connect's API does not expose option
# Greeks or implied volatility anywhere (confirmed against the Kite Connect developer forum,
# Sept 2026) — only LTP/OI. Delta-targeted strike selection needs delta from somewhere, so
# this solves it locally: given a contract's live LTP, numerically invert Black-Scholes for
# implied volatility, then compute delta from that IV. European, no dividend yield — NIFTY
# index options are close enough to this for strike selection purposes; this is not meant to
# be a precision pricing model.

import math
from typing import Optional

from scipy.stats import norm
from scipy.optimize import brentq

IV_LOWER_BOUND = 1e-4
IV_UPPER_BOUND = 5.0


def bs_price(spot: float, strike: float, dte_years: float, rate: float, vol: float, option_type: str) -> float:
    """European Black-Scholes price for a CE/PE. Falls back to intrinsic value at/after expiry or zero vol."""
    if dte_years <= 0 or vol <= 0:
        return max(0.0, (spot - strike) if option_type == "CE" else (strike - spot))

    sqrt_t = math.sqrt(dte_years)
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol ** 2) * dte_years) / (vol * sqrt_t)
    d2 = d1 - vol * sqrt_t

    if option_type == "CE":
        return spot * norm.cdf(d1) - strike * math.exp(-rate * dte_years) * norm.cdf(d2)
    return strike * math.exp(-rate * dte_years) * norm.cdf(-d2) - spot * norm.cdf(-d1)


def bs_delta(spot: float, strike: float, dte_years: float, rate: float, vol: float, option_type: str) -> float:
    """Black-Scholes delta for a CE/PE — CE in [0, 1], PE in [-1, 0]."""
    if dte_years <= 0 or vol <= 0:
        in_the_money = spot > strike if option_type == "CE" else spot < strike
        if not in_the_money:
            return 0.0
        return 1.0 if option_type == "CE" else -1.0

    sqrt_t = math.sqrt(dte_years)
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol ** 2) * dte_years) / (vol * sqrt_t)
    return norm.cdf(d1) if option_type == "CE" else norm.cdf(d1) - 1.0


def implied_volatility(price: float, spot: float, strike: float, dte_years: float, rate: float, option_type: str) -> Optional[float]:
    """Solve for the volatility that reprices `price` under Black-Scholes, via bounded root-finding.

    Returns None rather than raising whenever no solution exists in-bounds — a quote at or
    below intrinsic value (no time value left to explain) or a degenerate expiry, most often
    a stale/bad tick rather than a real arbitrage. Callers should treat None as "this contract
    isn't usable right now", not retry with a different bound.
    """
    if price <= 0 or dte_years <= 0:
        return None

    intrinsic = max(0.0, (spot - strike) if option_type == "CE" else (strike - spot))
    if price <= intrinsic:
        return None

    def objective(vol: float) -> float:
        return bs_price(spot, strike, dte_years, rate, vol, option_type) - price

    try:
        if objective(IV_LOWER_BOUND) * objective(IV_UPPER_BOUND) > 0:
            return None
        return brentq(objective, IV_LOWER_BOUND, IV_UPPER_BOUND, xtol=1e-6)
    except (ValueError, RuntimeError):
        return None


def estimate_delta(price: float, spot: float, strike: float, dte_years: float, rate: float, option_type: str) -> Optional[float]:
    """Solve implied vol from a contract's live LTP, then return its Black-Scholes delta. None if unsolvable."""
    iv = implied_volatility(price, spot, strike, dte_years, rate, option_type)
    if iv is None:
        return None
    return bs_delta(spot, strike, dte_years, rate, iv, option_type)
