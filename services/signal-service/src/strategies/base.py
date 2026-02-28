"""Base classes and interfaces for strategy calculation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class StrategyInput:
    """Input data for strategy calculation."""

    symbol: str
    interval: str
    kline_data: dict[str, Any]
    subscription_key: str
    computed_at: datetime


@dataclass(frozen=True)
class StrategyOutput:
    """Output data from strategy calculation."""

    signal_value: bool | None  # true=做多, false=做空, null=无信号
    signal_reason: str


class Strategy(ABC):
    """Abstract base class for strategy calculation."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get strategy name.

        Returns:
            Strategy name identifier.
        """
        ...

    @abstractmethod
    def calculate(self, input_data: StrategyInput) -> StrategyOutput:
        """Calculate strategy signal.

        Args:
            input_data: Input data containing symbol, interval, kline data.

        Returns:
            StrategyOutput containing signal value and reason.
        """
        ...
