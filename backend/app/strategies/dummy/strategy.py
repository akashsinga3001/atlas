# backend/app/strategies/dummy/strategy.py

from datetime import datetime

from app.strategies.base import Strategy
from app.strategies.context import StrategyContext
from app.strategies.observation import Observation


class DummyStrategy(Strategy):
    code = "dummy"
    name = "Dummy Strategy"

    async def execute(self, context: StrategyContext) -> list[Observation]:
        # This is a dummy strategy that generates random observations.
        # In a real implementation, replace this with actual strategy logic.
        return [Observation(security_id=1, observed_at=context.as_of_date, data={ "message": "Dummy Signal", "strategy": self.code })]
