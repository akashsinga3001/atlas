# backend/app/execution_engines/bootstrap.py

from app.execution_engines.registry import ExecutionEngineRegistry
from app.execution_engines.equity import EquityExecutionEngine
from app.execution_engines.options_iron_condor import OptionsIronCondorExecutionEngine


def register_execution_engines() -> None:
    """Registers all trade execution engines in the ExecutionEngineRegistry."""
    ExecutionEngineRegistry.register(EquityExecutionEngine)
    ExecutionEngineRegistry.register(OptionsIronCondorExecutionEngine)
