# backend/app/execution_engines/registry.py

from app.execution_engines.base import TradeExecutionEngine


class ExecutionEngineRegistry:
    """Registry for managing trade execution engines, allowing registration and retrieval by code."""
    _engines: dict[str, type[TradeExecutionEngine]] = {}

    @classmethod
    def register(cls, engine_class: type[TradeExecutionEngine]) -> None:
        cls._engines[engine_class.code] = engine_class

    @classmethod
    def get(cls, code: str) -> type[TradeExecutionEngine]:
        try:
            return cls._engines[code]
        except KeyError as exc:
            raise ValueError(f"Execution engine with code '{code}' not found in the registry.") from exc

    @classmethod
    def list(cls) -> list[str]:
        return sorted(cls._engines.keys())
