"""Tests for RandomStrategy."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.strategies.base import StrategyInput, StrategyOutput
from src.strategies.random_strategy import RandomStrategy


def _utcnow() -> datetime:
    """Get current UTC time in timezone-aware format."""
    return datetime.now(timezone.utc)


def test_random_strategy_name() -> None:
    """Test RandomStrategy returns correct name."""
    strategy = RandomStrategy()
    assert strategy.name == "random"


def test_random_strategy_calculate() -> None:
    """Test RandomStrategy.calculate returns valid output."""
    strategy = RandomStrategy()

    input_data = StrategyInput(
        symbol="BINANCE:BTCUSDT",
        interval="1",
        kline_data={"close": 50000.0, "open": 49900.0},
        subscription_key="BINANCE:BTCUSDT@KLINE_1",
        computed_at=_utcnow(),
    )

    # Run multiple times to ensure it returns valid values
    for _ in range(100):
        output = strategy.calculate(input_data)

        # Verify output structure
        assert isinstance(output, StrategyOutput)
        assert output.signal_value in [True, False, None]
        assert output.signal_reason in ["随机做多信号", "随机做空信号", "随机无信号（观望）"]


def test_random_strategy_distribution() -> None:
    """Test RandomStrategy returns variety of signals."""
    strategy = RandomStrategy()

    input_data = StrategyInput(
        symbol="BINANCE:BTCUSDT",
        interval="1",
        kline_data={"close": 50000.0},
        subscription_key="BINANCE:BTCUSDT@KLINE_1",
        computed_at=_utcnow(),
    )

    # Collect signals over many runs
    signals = set()
    for _ in range(100):
        output = strategy.calculate(input_data)
        signals.add(output.signal_value)

    # Should have at least 2 different signal values (True/False/None are all valid)
    # Random can occasionally return only 2 values, so we check for at least 2
    assert len(signals) >= 2
