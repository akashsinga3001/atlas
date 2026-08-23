# backend/app/schemas/strategy_config.py

from pydantic import BaseModel, Field


class NiftyIronCondorConfig(BaseModel):
    """Typed config schema for the nifty_iron_condor strategy, mirrors the keys seeded in d4e8b6c2a9f3/f7a3c1e9b4d2."""
    underlying_ticker: str = Field(..., description="NSE ticker for the underlying index")
    option_name: str = Field(..., description="Option chain root symbol")
    signal_day_of_week: int = Field(..., description="0=Monday .. 6=Sunday, day the weekly signal fires")
    strike_step: int = Field(..., description="Strike price increment for the underlying's option chain")
    short_otm_pct: float = Field(..., description="OTM distance for short strikes, as a fraction of spot")
    long_otm_pct: float = Field(..., description="OTM distance for long (protective) strikes, as a fraction of spot")
    capital_pct_calm: float = Field(..., description="Fraction of allocated capital to deploy per entry when the volatility regime is calm")
    capital_pct_elevated: float = Field(..., description="Fraction of allocated capital to deploy per entry when the volatility regime is elevated")
    max_lots: int = Field(..., description="Maximum lots per entry — a high, rarely-binding safety ceiling, not the primary risk control")
    hold_days: int = Field(..., description="Trading days to hold the position before scheduled exit")
    account_capital_pct: float = Field(1.0, description="Fraction of total account capital this strategy may use")
    vol_regime_lookback_days: int = Field(60, description="Trading days of realized volatility used for regime detection")
    liquidity_lookback_days: int = Field(5, description="Trading days of EOD wing-leg volume averaged for the live liquidity cap")
    liquidity_participation_pct: float = Field(0.05, description="Max fraction of trailing average wing-leg volume sizeable into in one entry")


STRATEGY_CONFIG_SCHEMAS: dict[str, type[BaseModel]] = {
    "nifty_iron_condor": NiftyIronCondorConfig,
}


def get_config_schema(implementation_class: str) -> type[BaseModel] | None:
    """Look up the registered Pydantic config schema for a strategy implementation_class, if any."""
    return STRATEGY_CONFIG_SCHEMAS.get(implementation_class)
