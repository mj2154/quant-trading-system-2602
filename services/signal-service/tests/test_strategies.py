"""Tests for strategy base module."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.strategies.base import Strategy, StrategyInput, StrategyOutput


class MockStrategy(Strategy):
    """Mock strategy for testing."""

    @property
    def name(self) -> str:
        return "mock"

    def calculate(self, input_data: StrategyInput) -> StrategyOutput:
        return StrategyOutput(
            signal_value=True,
            signal_reason="Test signal",
        )


def test_strategy_input_creation() -> None:
    """Test StrategyInput creation."""
    input_data = StrategyInput(
        symbol="BINANCE:BTCUSDT",
        interval="1",
        kline_data={"close": 50000.0},
        subscription_key="BINANCE:BTCUSDT@KLINE_1",
        computed_at=datetime.now(timezone.utc),
    )

    assert input_data.symbol == "BINANCE:BTCUSDT"
    assert input_data.interval == "1"
    assert input_data.kline_data["close"] == 50000.0


def test_strategy_output_creation() -> None:
    """Test StrategyOutput creation."""
    output = StrategyOutput(
        signal_value=True,
        signal_reason="Test reason",
    )

    assert output.signal_value is True
    assert output.signal_reason == "Test reason"


def test_strategy_output_null_signal() -> None:
    """Test StrategyOutput with null signal."""
    output = StrategyOutput(
        signal_value=None,
        signal_reason="No signal",
    )

    assert output.signal_value is None


def test_strategy_implementation() -> None:
    """Test Strategy interface implementation."""
    strategy = MockStrategy()

    assert strategy.name == "mock"

    input_data = StrategyInput(
        symbol="BINANCE:BTCUSDT",
        interval="1",
        kline_data={"close": 50000.0},
        subscription_key="BINANCE:BTCUSDT@KLINE_1",
        computed_at=datetime.now(timezone.utc),
    )

    output = strategy.calculate(input_data)

    assert output.signal_value is True
    assert output.signal_reason == "Test signal"
