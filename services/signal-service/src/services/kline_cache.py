"""K-line cache management utilities."""
import logging
from typing import Any

import pandas as pd

from .constants import REQUIRED_KLINES

logger = logging.getLogger(__name__)


def _update_kline_cache(
    cache: dict[str, pd.DataFrame],
    subscription_key: str,
    kline_data: dict[str, Any],
    required_klines: int = REQUIRED_KLINES,
) -> bool:
    """Incrementally update K-line cache based on time field.

    - If cache already has a kline with the same time -> update that row
    - If cache doesn't have that time -> append to the end
    - If cache exceeds required_klines -> remove oldest (first) row

    Args:
        cache: K-line cache dictionary.
        subscription_key: Subscription key (e.g., "BINANCE:BTCUSDT@KLINE_60").
        kline_data: New K-line data from realtime.update.
        required_klines: Required number of klines (default 280).

    Returns:
        True if cache was updated, False if cache not initialized.
    """
    if subscription_key not in cache:
        # Cache not initialized, return False to indicate initial load needed
        return False

    # Convert Binance format to DataFrame row format
    # Binance format: {"e": "kline", "k": {"o": "...", "h": "...", "l": "...", "c": "...", "v": "...", "t": ...}, "s": "BTCUSDT"}
    # DataFrame columns: time (int), open, high, low, close, volume (numeric)
    k = kline_data.get("k", kline_data)
    new_time = k.get("t")
    new_row = pd.DataFrame([{
        "time": new_time,
        "open": float(k.get("o")) if k.get("o") else None,
        "high": float(k.get("h")) if k.get("h") else None,
        "low": float(k.get("l")) if k.get("l") else None,
        "close": float(k.get("c")) if k.get("c") else None,
        "volume": float(k.get("v")) if k.get("v") else None,
    }])

    current_cache = cache[subscription_key].copy()

    # Check if a kline with the same time already exists in cache
    existing_indices = current_cache[current_cache["time"] == new_time].index.tolist()

    if existing_indices:
        # Update existing row
        idx = existing_indices[0]
        current_cache.loc[idx] = new_row.iloc[0]
    else:
        # New time -> append to end
        current_cache = pd.concat([current_cache, new_row], ignore_index=True)

        # Trim to required size (keep latest)
        if len(current_cache) > required_klines:
            current_cache = current_cache.iloc[-required_klines:]

    cache[subscription_key] = current_cache
    return True


def _init_kline_cache(
    cache: dict[str, pd.DataFrame],
    subscription_key: str,
    history: list[dict[str, Any]],
    required_klines: int = REQUIRED_KLINES,
) -> None:
    """Initialize K-line cache from history.

    Args:
        cache: K-line cache dictionary.
        subscription_key: Subscription key.
        history: Historical klines from database (database raw format).
        required_klines: Required number of klines.
    """
    # DEBUG: Log input info
    logger.info(
        "_init_kline_cache: subscription_key=%s history_count=%d required_klines=%d",
        subscription_key,
        len(history),
        required_klines,
    )

    # Convert database raw format to DataFrame
    # Database fields: open_price, high_price, low_price, close_price, volume, open_time
    # DataFrame columns (aligned with backtest fetch_klines): time, open, high, low, close, volume
    rows = history[:required_klines]
    logger.info("_init_kline_cache: Using %d rows from history", len(rows))

    if not rows:
        cache[subscription_key] = pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
        logger.info("_init_kline_cache: Empty history, initialized empty DataFrame")
        return

    data = []
    for row in rows:
        # Convert TIMESTAMPTZ to milliseconds timestamp
        open_time = row.get("open_time")
        if hasattr(open_time, 'timestamp'):
            time_ms = int(open_time.timestamp() * 1000)
        else:
            time_ms = open_time

        data.append({
            "time": time_ms,
            "open": float(row.get("open_price")) if row.get("open_price") else None,
            "high": float(row.get("high_price")) if row.get("high_price") else None,
            "low": float(row.get("low_price")) if row.get("low_price") else None,
            "close": float(row.get("close_price")) if row.get("close_price") else None,
            "volume": float(row.get("volume")) if row.get("volume") else None,
        })

    cache[subscription_key] = pd.DataFrame(data)
