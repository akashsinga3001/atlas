# backend/app/strategies/observation.py

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Observation:
    """
    Represents an observation made by a strategy.

    Attributes:
        observed_at (datetime): The time when the observation was made.
        data (dict[str, Any]): The data associated with the observation.
    """
    observed_at: datetime
    data: dict[str, Any]
