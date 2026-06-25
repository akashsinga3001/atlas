# backend/app/exit_evaluators/registry.py

from app.exit_evaluators.base import ExitEvaluator


class ExitEvaluatorRegistry:
    """Registry for managing exit evaluators, allowing registration and retrieval by code."""
    _evaluators: dict[str, type[ExitEvaluator]] = {}

    @classmethod
    def register(cls, evaluator_class: type[ExitEvaluator]) -> None:
        cls._evaluators[evaluator_class.code] = evaluator_class

    @classmethod
    def get(cls, code: str) -> type[ExitEvaluator]:
        try:
            return cls._evaluators[code]
        except KeyError as exc:
            raise ValueError(f"Exit evaluator with code '{code}' not found in the registry.") from exc

    @classmethod
    def list(cls) -> list[str]:
        return sorted(cls._evaluators.keys())
