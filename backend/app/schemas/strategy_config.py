# backend/app/schemas/strategy_config.py

from pydantic import BaseModel, ConfigDict, Field


class MomentumScreenerConfig(BaseModel):
    """Typed config schema for the momentum_screener strategy.

    Only account_capital_pct is modeled explicitly — the rest of the live config
    (entry/exit/setup/selection) is nested, and the generic config UI only renders
    flat scalar/enum/array fields. extra="allow" passes those nested keys through
    validation untouched instead of rejecting or flattening them.
    """
    model_config = ConfigDict(extra="allow")
    account_capital_pct: float = Field(1.0, description="Fraction of total account capital this strategy may use")


class NiftyIronCondorConfig(BaseModel):
    """Typed config schema for the nifty_iron_condor strategy (delta-targeted, VIX-gated version)."""
    underlying_ticker: str = Field(..., description="NSE ticker for the underlying index")
    option_name: str = Field(..., description="Option chain root symbol")
    vix_ticker: str = Field(..., description="NSE ticker for the India VIX index")
    entry_dte_target: int = Field(..., description="Target days-to-expiry for entry — nearest listed expiry is selected")
    short_delta_target: float = Field(..., description="Target |delta| for short strikes (e.g. 0.20 for ~20-delta)")
    delta_tolerance: float = Field(..., description="Max deviation from short_delta_target a strike may have to qualify")
    wing_width_points: float = Field(..., description="Distance in strike points from each short strike to its protective long strike")
    profit_target_pct: float = Field(..., description="Exit when cost-to-close falls to this fraction of the real entry credit")
    stop_loss_multiple: float = Field(..., description="Exit when cost-to-close rises to this multiple of the real entry credit")
    time_exit_dte: int = Field(..., description="Force-close once this many calendar days or fewer remain to expiry")
    vix_percentile_lookback_days: int = Field(..., description="Trailing days of India VIX history the entry percentile gate is computed against")
    vix_avoid_band_low: float = Field(..., description="Entry is rejected when VIX percentile falls strictly between this and vix_avoid_band_high")
    vix_avoid_band_high: float = Field(..., description="Entry is rejected when VIX percentile falls strictly between vix_avoid_band_low and this")
    max_lots: int = Field(..., description="Hard cap on lots per entry regardless of what the capital math alone allows")
    risk_free_rate: float = Field(..., description="Annualised risk-free rate used by the Black-Scholes IV solve/delta calc")
    live_trading_enabled: bool = Field(False, description="When false (default), entries/exits simulate fills against live quotes instead of placing real Kite orders — paper trading")
    account_capital_pct: float = Field(1.0, description="Fraction of total account capital this strategy may use")


STRATEGY_CONFIG_SCHEMAS: dict[str, type[BaseModel]] = {
    "nifty_iron_condor": NiftyIronCondorConfig,
    "momentum_screener": MomentumScreenerConfig,
}


def get_config_schema(implementation_class: str) -> type[BaseModel] | None:
    """Look up the registered Pydantic config schema for a strategy implementation_class, if any."""
    return STRATEGY_CONFIG_SCHEMAS.get(implementation_class)
