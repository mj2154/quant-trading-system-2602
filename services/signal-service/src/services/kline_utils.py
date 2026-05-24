"""K-line data utilities."""
import time
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pandas as pd

from .constants import TV_INTERVAL_TO_MS


def _format_kline_time(time_value: Any) -> str:
    """Format kline time value to China Standard Time (UTC+8) string.

    Args:
        time_value: Time value - can be:
            - Milliseconds timestamp (int/str) from Binance
            - ISO format string from database

    Returns:
        Formatted time string in CST (e.g., "2026-02-20 15:30:00")
    """
    if time_value is None:
        return "None"

    try:
        # Try milliseconds timestamp (Binance format)
        if isinstance(time_value, str):
            time_value = int(time_value)
        dt = datetime.fromtimestamp(time_value / 1000, tz=UTC)
        cst = dt.astimezone(timezone(timedelta(hours=8)))
        return cst.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        pass

    # Try ISO format string
    try:
        if isinstance(time_value, str):
            # Handle both formats: "2026-02-20T07:10:00+08:00" and "2026-02-20T07:10:00+00:00"
            dt = datetime.fromisoformat(time_value.replace("Z", "+00:00"))
            # Convert to CST if not already
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            cst = dt.astimezone(timezone(timedelta(hours=8)))
            return cst.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        pass

    return str(time_value)


def _build_ohlcv_for_trigger_type(history: pd.DataFrame) -> pd.DataFrame:
    """Return cached history as-is for strategy calculation.

    Cache is always updated before this function is called, so no additional
    processing is needed.
    """
    return history.copy()


def _get_interval_ms(interval: str) -> int:
    """Get interval in milliseconds.

    Args:
        interval: TV format interval (1, 5, 60, D, etc.)

    Returns:
        Interval in milliseconds.
    """
    return TV_INTERVAL_TO_MS.get(interval, 60 * 60 * 1000)


def _convert_time_to_ms(time_value: Any) -> int | None:
    """Convert time value to milliseconds integer for comparison."""
    if time_value is None:
        return None
    if hasattr(time_value, 'timestamp'):
        return int(time_value.timestamp() * 1000)
    return int(time_value)


def _get_previous_period_time(interval: str) -> int:
    """Calculate the previous period start time in milliseconds.

    Args:
        interval: TV format interval (1, 5, 60, D, etc.)

    Returns:
        Previous period start time in milliseconds (UTC).
    """
    now_ms = int(time.time() * 1000)
    interval_ms = _get_interval_ms(interval)

    # Align to period boundary
    period_start = (now_ms // interval_ms) * interval_ms
    return period_start - interval_ms
