# Lazy re-export: engine.py imports OptionsTradeService, which itself imports this package's
# `logic` submodule for pure decision math. Eagerly importing engine.py here (as the equity
# engine's __init__.py does for its own engine) would make that a circular import whenever
# something imports `logic` before `OptionsIronCondorExecutionEngine` — deferring the engine
# import to first attribute access breaks the cycle without changing any external import site.
__all__ = ["OptionsIronCondorExecutionEngine"]


def __getattr__(name: str):
    if name == "OptionsIronCondorExecutionEngine":
        from app.execution_engines.options_iron_condor.engine import OptionsIronCondorExecutionEngine
        return OptionsIronCondorExecutionEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
