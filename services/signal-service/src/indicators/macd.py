"""MACD (Moving Average Convergence Divergence) indicator implementation."""

from dataclasses import dataclass

from .ema import calculate_ema


@dataclass(frozen=True)
class MacdResult:
    """MACD calculation result."""

    macd_line: list[float]  # MACD line = fast_ema - slow_ema
    signal_line: list[float]  # Signal line = EMA of MACD line
    histogram: list[float]  # Histogram = macd_line - signal_line
    fast_period: int
    slow_period: int
    signal_period: int


def calculate_macd(
    prices: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> MacdResult:
    """Calculate MACD indicator.

    MACD Line = Fast EMA - Slow EMA
    Signal Line = EMA of MACD Line
    Histogram = MACD Line - Signal Line

    Args:
        prices: List of close prices.
        fast_period: Fast EMA period (default: 12).
        slow_period: Slow EMA period (default: 26).
        signal_period: Signal line EMA period (default: 9).

    Returns:
        MacdResult containing MACD line, signal line, and histogram.
        Values are aligned starting from index (slow_period + signal_period - 2).
    """
    if len(prices) < slow_period:
        # Return empty result if insufficient data
        return MacdResult(
            macd_line=[],
            signal_line=[],
            histogram=[],
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
        )

    # Calculate fast and slow EMAs
    fast_ema_result = calculate_ema(prices, fast_period)
    slow_ema_result = calculate_ema(prices, slow_period)

    # Align EMAs: both start from index (slow_period - 1)
    # fast_ema starts from index (fast_period - 1), slow_ema from (slow_period - 1)
    # We need to align them properly

    # Calculate MACD line: fast_ema - slow_ema
    # Fast EMA is calculated over shorter period, so it has more values
    # We need to find the overlapping range
    fast_start = fast_period - 1
    slow_start = slow_period - 1

    # Find the start index for both in the original price array
    # Fast EMA values start at price[fast_period - 1]
    # Slow EMA values start at price[slow_period - 1]
    # MACD requires both, so start from max(fast_start, slow_start)
    start_idx = max(fast_start, slow_start)

    # Get aligned EMAs
    fast_ema_aligned = fast_ema_result.values[(start_idx - fast_start):]
    slow_ema_aligned = slow_ema_result.values[(start_idx - slow_start):]

    # Calculate MACD line
    macd_line = [f - s for f, s in zip(fast_ema_aligned, slow_ema_aligned)]

    # Calculate Signal line (EMA of MACD line)
    if len(macd_line) < signal_period:
        return MacdResult(
            macd_line=[],
            signal_line=[],
            histogram=[],
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
        )

    signal_ema_result = calculate_ema(macd_line, signal_period)
    signal_line = signal_ema_result.values

    # Calculate Histogram: MACD line - Signal line
    # Signal line starts from signal_period - 1 in the MACD line
    # So we need to align them properly
    macd_start_for_histogram = signal_period - 1
    if len(macd_line) > macd_start_for_histogram:
        macd_for_histogram = macd_line[macd_start_for_histogram:]
        histogram = [m - s for m, s in zip(macd_for_histogram, signal_line)]
    else:
        histogram = []

    return MacdResult(
        macd_line=macd_line,
        signal_line=signal_line,
        histogram=histogram,
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
    )


def get_macd_signal(macd_result: MacdResult) -> int | None:
    """Get MACD signal from the latest values.

    Args:
        macd_result: MACD calculation result.

    Returns:
        1 if bullish (MACD line > Signal line, i.e., golden cross)
        -1 if bearish (MACD line < Signal line, i.e., death cross)
        None if insufficient data.
    """
    if not macd_result.histogram or len(macd_result.histogram) < 2:
        return None

    # Check the latest histogram value
    latest_histogram = macd_result.histogram[-1]

    if latest_histogram > 0:
        return 1  # Bullish: MACD above signal
    elif latest_histogram < 0:
        return -1  # Bearish: MACD below signal
    else:
        return 0  # Neutral


def is_golden_cross(macd_result: MacdResult) -> bool:
    """Check if there's a golden cross (bullish crossover).

    Golden cross: MACD line crosses above signal line (histogram goes from negative to positive).

    Args:
        macd_result: MACD calculation result.

    Returns:
        True if golden cross detected, False otherwise.
    """
    if not macd_result.histogram or len(macd_result.histogram) < 2:
        return False

    # Golden cross: previous histogram < 0, current histogram >= 0
    prev_histogram = macd_result.histogram[-2]
    curr_histogram = macd_result.histogram[-1]

    return prev_histogram < 0 and curr_histogram >= 0


def is_death_cross(macd_result: MacdResult) -> bool:
    """Check if there's a death cross (bearish crossover).

    Death cross: MACD line crosses below signal line (histogram goes from positive to negative).

    Args:
        macd_result: MACD calculation result.

    Returns:
        True if death cross detected, False otherwise.
    """
    if not macd_result.histogram or len(macd_result.histogram) < 2:
        return False

    # Death cross: previous histogram > 0, current histogram <= 0
    prev_histogram = macd_result.histogram[-2]
    curr_histogram = macd_result.histogram[-1]

    return prev_histogram > 0 and curr_histogram <= 0
