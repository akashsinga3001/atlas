# backend/app/strategies/registry.py

from app.strategies.base import Strategy


class StrategyRegistry:
    """
    A registry for managing and retrieving strategy classes.

    This class allows for the registration of strategy classes and provides
    methods to retrieve them by name. It serves as a central repository for
    strategy implementations, enabling dynamic access to different strategies
    based on their names.

    Attributes:
        _registry (dict[str, type[Strategy]]): A dictionary mapping strategy names to their corresponding strategy classes.
    """

    _strategies: dict[str, type[Strategy]] = {}

    @classmethod
    def register(cls, strategy_class: type[Strategy]) -> None:
        """
        Register a strategy class in the registry.

        Args:
            strategy_class (type[Strategy]): The strategy class to register.
        """
        cls._strategies[strategy_class.code] = strategy_class

    @classmethod
    def get(cls, strategy_code: str) -> type[Strategy]:
        """
        Retrieve a strategy class from the registry by its code.

        Args:
            strategy_code (str): The code of the strategy to retrieve.

        Returns:
            type[Strategy]: The strategy class associated with the given code.

        Raises:
            ValueError: If no strategy with the given code is found.
        """
        try:
            return cls._strategies[strategy_code]
        except KeyError as exc:
            raise ValueError(f"Strategy with code '{strategy_code}' not found in the registry.") from exc

    @classmethod
    def list(cls) -> list[str]:
        """
        List all registered strategy codes.

        Returns:
            list[str]: A list of all registered strategy codes.
        """
        return sorted(cls._strategies.keys())
