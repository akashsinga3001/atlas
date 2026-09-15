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


class RelativeLeadershipV1Config(BaseModel):
    """Typed config schema for the relative_leadership_v1 strategy.

    This strategy's rules are frozen per its spec — only account_capital_pct is UI-editable.
    Every other key (momentum offsets, percentile thresholds, confirmation window,
    selection.max_signals, execution params) is a frozen V1 constant carried in config for
    parity with the rest of the strategy framework's versioning mechanism, not meant to be
    tuned via the generic UI — changing any of them defines a new strategy version, per the
    spec's own versioning rule. extra="allow" passes those nested keys through untouched,
    same as MomentumScreenerConfig.
    """
    model_config = ConfigDict(extra="allow")
    account_capital_pct: float = Field(1.0, description="Fraction of total account capital this strategy may use")


STRATEGY_CONFIG_SCHEMAS: dict[str, type[BaseModel]] = {
    "momentum_screener": MomentumScreenerConfig,
    "relative_leadership_v1": RelativeLeadershipV1Config,
}


def get_config_schema(implementation_class: str) -> type[BaseModel] | None:
    """Look up the registered Pydantic config schema for a strategy implementation_class, if any."""
    return STRATEGY_CONFIG_SCHEMAS.get(implementation_class)
