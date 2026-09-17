# backend/app/strategies/context.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, TYPE_CHECKING

from app.services.feature import FeatureService

if TYPE_CHECKING:
    from app.services.quote import QuoteService


@dataclass(slots=True)
class StrategyContext:
    """
    Represents the context in which a strategy operates.

    Attributes:
        as_of_date (datetime): The date for which the context is relevant.
        feature_service (FeatureService): Read access to persisted OHLCV-derived features.
        config (dict[str, Any]): The parameters associated with the strategy context.
        quote_service_factory (Callable[[], QuoteService]): Builds a QuoteService on demand for
            strategies that need a live broker quote (e.g. an intraday spot price not yet in the
            OHLCV/feature store). Deliberately a factory rather than a pre-built instance —
            QuoteService's default KiteService() launches a headless browser on construction, so
            eagerly building one for every strategy run would pay that cost even for strategies
            (e.g. momentum_screener) that never touch it.
        previous_run_metrics (dict[str, Any]): Whatever the strategy's own build_run_metrics()
            returned on its last COMPLETED run for this strategy version, or {} if there wasn't
            one. Generic on purpose — most strategies ignore it, same as quote_service_factory is
            ignored by strategies with no live-quote need — but it's how a strategy reads back a
            fact it committed on a prior day instead of re-deriving that day from scratch.
    """
    as_of_date: datetime
    feature_service: FeatureService
    config: dict[str, Any]
    quote_service_factory: "Callable[[], QuoteService]"
    previous_run_metrics: dict[str, Any] = field(default_factory=dict)
