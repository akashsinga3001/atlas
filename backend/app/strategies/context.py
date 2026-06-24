# backend/app/strategies/context.py

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.services.feature import FeatureService


@dataclass(slots=True)
class StrategyContext:
    """
    Represents the context in which a strategy operates.

    Attributes:
        as_of_date (datetime): The date for which the context is relevant.
        parameters (dict[str, Any]): The parameters associated with the strategy context.
    """
    as_of_date: datetime
    feature_service: FeatureService
    config: dict[str, Any]
