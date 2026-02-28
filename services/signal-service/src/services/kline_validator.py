"""K-line validation utilities."""
from typing import Any

from .constants import REQUIRED_KLINES
from .kline_utils import _get_interval_ms, _get_previous_period_time


def _check_kline_continuity(history: list[dict[str, Any]], interval: str) -> bool:
    """Check if klines are continuous (no time gaps).

    Args:
        history: List of kline records from database.
        interval: TV format interval.

    Returns:
        True if continuous, False if there are gaps.
    """
    if len(history) < 2:
        return True

    interval_ms = _get_interval_ms(interval)

    for i in range(1, len(history)):
        prev_time = history[i - 1].get("open_time")
        curr_time = history[i].get("open_time")

        if prev_time is None or curr_time is None:
            continue

        # Convert to milliseconds
        if hasattr(prev_time, "timestamp"):
            prev_ms = int(prev_time.timestamp() * 1000)
        else:
            prev_ms = prev_time

        if hasattr(curr_time, "timestamp"):
            curr_ms = int(curr_time.timestamp() * 1000)
        else:
            curr_ms = curr_time

        # Check time difference
        diff = curr_ms - prev_ms
        if abs(diff - interval_ms) > 1000:  # Allow 1 second tolerance
            return False

    return True


def _check_last_kline_time(history: list[dict[str, Any]], interval: str) -> bool:
    """Check if the last kline time is the previous period.

    Args:
        history: List of kline records from database.
        interval: TV format interval.

    Returns:
        True if last kline is the previous period, False otherwise.
    """
    if not history:
        return False

    last_kline = history[-1]
    last_time = last_kline.get("open_time")

    if last_time is None:
        return False

    # Convert to milliseconds
    if hasattr(last_time, "timestamp"):
        last_ms = int(last_time.timestamp() * 1000)
    else:
        last_ms = last_time

    # Get previous period time
    previous_period_ms = _get_previous_period_time(interval)

    # Allow 2 minute tolerance for "previous period" check
    tolerance = 2 * 60 * 1000

    return abs(last_ms - previous_period_ms) <= tolerance


def _check_kline_data_validity(
    history: list[dict[str, Any]],
    interval: str,
    required_count: int = REQUIRED_KLINES,
) -> tuple[bool, str]:
    """Check if kline data meets two conditions (quantity and continuity).

    Note: Time correctness (last kline is latest period) is NOT checked at startup.
    Time correctness is checked at runtime via realtime update detection.
    This avoids infinite retry loops when network is down during startup.

    Args:
        history: List of kline records from database.
        interval: TV format interval.
        required_count: Required minimum number of klines.

    Returns:
        Tuple of (is_valid, reason).
    """
    # Check 1: Quantity
    if len(history) < required_count:
        return False, f"insufficient_count:{len(history)}/{required_count}"

    # Check 2: Continuity
    if not _check_kline_continuity(history, interval):
        return False, "not_continuous"

    # Note: Time correctness check removed - handled at runtime via realtime update
    # This prevents infinite retry loops when network is unavailable during startup

    return True, "ok"
