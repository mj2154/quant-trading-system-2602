"""Strategies module for signal service."""
from .backtest_base import BaseStrategy, StrategySignals
from .base import Strategy, StrategyInput, StrategyOutput
from .macd_resonance_strategy import (
    MACDResonanceShortStrategy,
    MACDResonanceShortStrategyV1,
    MACDResonanceStrategyV5,
    MACDResonanceStrategyV6,
    MACDResonanceStrategyV601,
)
from .random_strategy import RandomStrategy
from .registry import StrategyMetadata, StrategyParam, StrategyRegistry

__all__ = [
    "Strategy",
    "StrategyInput",
    "StrategyOutput",
    "RandomStrategy",
    "MACDResonanceStrategyV5",
    "MACDResonanceStrategyV6",
    "MACDResonanceStrategyV601",
    "MACDResonanceShortStrategy",
    "MACDResonanceShortStrategyV1",
    "BaseStrategy",
    "StrategySignals",
    "StrategyRegistry",
    "StrategyMetadata",
    "StrategyParam",
]
