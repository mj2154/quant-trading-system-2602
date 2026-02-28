"""Exponential Moving Average (EMA) indicator implementation."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EmaResult:
    """EMA calculation result."""

    values: list[float]
    period: int


def calculate_ema(prices: list[float], period: int) -> EmaResult:
    """Calculate Exponential Moving Average.

    Uses the standard EMA formula:
    EMA_today = (Price_today * k) + (EMA_yesterday * (1-k))
    where k = 2 / (period + 1)

    Args:
        prices: List of price values (typically close prices).
        period: EMA period (e.g., 12, 26 for MACD).

    Returns:
        EmaResult containing EMA values aligned with input prices.
        Returns empty list if insufficient data (< period).
    """
    if len(prices) < period:
        return EmaResult(values=[], period=period)

    # Convert to numpy array for efficient calculation
    price_array = np.array(prices, dtype=np.float64)

    # Multiplier k = 2 / (period + 1)
    k = 2.0 / (period + 1)

    # Initialize EMA with SMA (Simple Moving Average) of first 'period' prices
    ema_values: list[float] = []
    sma = float(np.mean(price_array[:period]))
    ema_values.append(sma)

    # Calculate EMA for remaining values
    for i in range(period, len(price_array)):
        ema_today = (price_array[i] * k) + (ema_values[-1] * (1 - k))
        ema_values.append(ema_today)

    return EmaResult(values=ema_values, period=period)


def calculate_ema_latest(prices: list[float], period: int) -> float | None:
    """Get the latest EMA value.

    Args:
        prices: List of price values.
        period: EMA period.

    Returns:
        Latest EMA value or None if insufficient data.
    """
    result = calculate_ema(prices, period)
    if result.values:
        return result.values[-1]
    return None
