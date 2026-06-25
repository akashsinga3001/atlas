# backend/app/exit_evaluators/context.py

from dataclasses import dataclass, field
from datetime import date

from app.models.trade import Trade


@dataclass
class ExitEvaluatorContext:
    """Context class for exit evaluators, containing relevant trade information."""
    trade: Trade
    as_of_date: date
    close_price: float
    features: dict = field(default_factory=dict)
