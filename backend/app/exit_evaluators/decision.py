# backend/app/exit_evaluators/decision.py

from dataclasses import dataclass, field

from app.enums.trade import ExitReason


@dataclass
class ExitDecision:
    """Class representing the decision made by an exit evaluator regarding whether to exit a trade."""
    should_exit: bool
    exit_reason: ExitReason | None = None
    state_update: dict = field(default_factory=dict)
    snapshot_state: dict = field(default_factory=dict)
