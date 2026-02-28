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


def _convert_klines_to_dataframe(
    klines: list[dict[str, Any]],
) -> pd.DataFrame:
    """Convert klines list to DataFrame.

    Args:
        klines: List of kline dictionaries with 'o', 'h', 'l', 'c', 'v' keys.

    Returns:
        DataFrame with open, high, low, close, volume columns.
    """
    if not klines:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    # Convert to DataFrame
    df = pd.DataFrame(klines)

    # Rename columns to standard format
    column_mapping = {
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "v": "volume",
    }
    df = df.rename(columns=column_mapping)

    # Keep only required columns
    required_cols = ["open", "high", "low", "close", "volume"]
    df = df[[col for col in required_cols if col in df.columns]]

    # Convert to numeric
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def _build_ohlcv_for_trigger_type(
    history: pd.DataFrame,
    current_kline: dict[str, Any] | None,
    trigger_type: str,
) -> pd.DataFrame:
    """Build ohlcv DataFrame based on trigger type.

    Note: Cache already contains the latest kline (updated in _update_kline_cache).
    This function just returns the cache as-is.

    Args:
        history: Historical klines as DataFrame (already contains latest kline).
        current_kline: Current realtime kline data (unused, cache has it).
        trigger_type: Trigger type (each_kline_close, each_kline, each_minute).

    Returns:
        DataFrame ready for strategy calculation.
    """
    # Cache already contains the latest data, just return it
    return history.copy()


def _convert_binance_kline_to_standard(kline_data: dict[str, Any]) -> dict[str, Any]:
    """Convert Binance kline format to standard format.

    Binance format: {"e": "kline", "k": {"o": "...", "h": "...", "l": "...", "c": "...", "v": "...", "t": ...}, "s": "BTCUSDT"}
    Standard format: {"o": "...", "h": "...", "l": "...", "c": "...", "v": "...", "t": ...}

    Args:
        kline_data: Binance format kline data.

    Returns:
        Standard format kline data with time field preserved.
    """
    if "k" in kline_data:
        k = kline_data["k"]
        return {
            "o": k.get("o"),
            "h": k.get("h"),
            "l": k.get("l"),
            "c": k.get("c"),
            "v": k.get("v"),
            "t": k.get("t"),  # Preserve open time timestamp (milliseconds)
            "ot": k.get("t"),  # Alias for open_time (for consistency with DB format)
        }
    return kline_data


def _get_interval_ms(interval: str) -> int:
    """Get interval in milliseconds.

    Args:
        interval: TV format interval (1, 5, 60, D, etc.)

    Returns:
        Interval in milliseconds.
    """
    return TV_INTERVAL_TO_MS.get(interval, 60 * 60 * 1000)


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
