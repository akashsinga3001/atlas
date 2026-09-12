# backend/app/execution_engines/options_iron_condor/logic.py
#
# Pure decision math for the delta-targeted NIFTY iron condor: expiry/strike selection,
# position sizing, and exit-priority evaluation. Extracted as standalone functions (no DB/
# broker access) so this — the logic that actually sizes and exits real capital — is
# independently auditable and unit-testable in isolation, mirroring the
# compute_vol_regime()-in-strategy.py convention but at the execution-engine layer, where
# this strategy's sizing/exit logic actually lives.

from datetime import date
from typing import Optional

from app.enums.options import OptionsExitReason


def select_nearest_dte_expiry(expiries: list[date], as_of_date: date, target_dte: int) -> Optional[date]:
    """Pick the listed expiry whose calendar-day DTE from as_of_date is closest to target_dte."""
    if not expiries:
        return None
    return min(expiries, key=lambda expiry: abs((expiry - as_of_date).days - target_dte))


def select_delta_target_strike(candidates: list[tuple[float, float]], target_delta: float, tolerance: float) -> Optional[float]:
    """Pick the strike whose |delta| is nearest target_delta, among candidates within tolerance.

    candidates: list of (strike, abs_delta) pairs. Returns None if none qualify — the caller
    must skip rather than fall back to the nearest available strike outside tolerance.
    """
    within_tolerance = [c for c in candidates if abs(c[1] - target_delta) <= tolerance]
    if not within_tolerance:
        return None
    return min(within_tolerance, key=lambda c: (abs(c[1] - target_delta), c[0]))[0]


def compute_wing_strike(short_strike: float, wing_width_points: float, option_type: str) -> float:
    """The protective long strike is wing_width_points beyond its corresponding short strike."""
    return short_strike + wing_width_points if option_type == "CE" else short_strike - wing_width_points


def compute_spread_value(short_call: float, short_put: float, long_call: float, long_put: float) -> float:
    """Net value of the 4-leg spread at a given set of per-leg prices.

    Same formula whether the prices are entry fills (-> net credit received) or current
    LTPs (-> cost to close): (short_call + short_put) - (long_call + long_put).
    """
    return (short_call + short_put) - (long_call + long_put)


def compute_max_loss_per_lot(wing_width_points: float, net_credit_per_lot: float, lot_size: int) -> float:
    """Defined max loss per lot: wing width minus credit received, times lot size. Logged for
    visibility at entry time — no longer the sizing divisor (see compute_position_size), since
    sizing now goes by real broker margin instead of this self-defined worst-case figure."""
    return (wing_width_points - net_credit_per_lot) * lot_size


def compute_position_size(capital: float, margin_per_lot: float, max_lots: int) -> int:
    """Size lots by how many fit inside available capital given the REAL broker margin required
    per lot (from KiteService.get_basket_order_margins, post-hedge-benefit), floored (never
    rounded up), hard-capped at max_lots regardless of what the capital math alone allows.
    No risk-fraction cap — capital and margin are the only inputs. Returns 0 if unsizeable."""
    if capital <= 0 or margin_per_lot <= 0:
        return 0
    lots = int(capital // margin_per_lot)
    return max(0, min(lots, max_lots))


def evaluate_exit_reason(days_to_expiry: int, real_entry_credit: Optional[float], cost_to_close: Optional[float], time_exit_dte: int, profit_target_pct: float, stop_loss_multiple: float) -> Optional[OptionsExitReason]:
    """Evaluate the 4-leg exit priority chain for one day, in the exact required order:

    1. Expiry safety exit (days_to_expiry <= 0)
    2. Time exit (days_to_expiry <= time_exit_dte), regardless of P&L
    3. Credit reconciliation guard: real_entry_credit computed from actual fills, not any
       earlier decision-time quote — if <= 0 the position filled as a net debit, close
       immediately rather than dividing by a non-positive denominator.
    4. Profit target: cost_to_close <= profit_target_pct * real_entry_credit
    5. Stop loss: cost_to_close >= stop_loss_multiple * real_entry_credit
    6. Otherwise hold (None).

    real_entry_credit/cost_to_close as None (not yet available — e.g. fills or quotes not
    fetched) holds rather than exiting, once the two priority checks that don't need them
    (expiry/time) are already ruled out.
    """
    if days_to_expiry <= 0:
        return OptionsExitReason.EXPIRY_EXIT
    if days_to_expiry <= time_exit_dte:
        return OptionsExitReason.TIME_EXIT

    if real_entry_credit is None:
        return None
    if real_entry_credit <= 0:
        return OptionsExitReason.CREDIT_RECONCILIATION

    if cost_to_close is None:
        return None
    if cost_to_close <= profit_target_pct * real_entry_credit:
        return OptionsExitReason.PROFIT_TARGET
    if cost_to_close >= stop_loss_multiple * real_entry_credit:
        return OptionsExitReason.STOP_LOSS

    return None
