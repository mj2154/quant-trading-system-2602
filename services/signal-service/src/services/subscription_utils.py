"""Subscription key utilities."""


def _build_subscription_key(symbol: str, interval: str) -> str:
    """Build subscription key following the architecture design.

    Format: {EXCHANGE}:{SYMBOL}@{DATA_TYPE}_{TV_RESOLUTION}
    - EXCHANGE: BINANCE (default)
    - DATA_TYPE: KLINE
    - TV_RESOLUTION: TradingView format (1, 60, D, etc.)

    Args:
        symbol: Trading pair symbol (e.g., "BINANCE:BTCUSDT" or "BTCUSDT")
        interval: Interval in TV format (1, 60, D) or Binance format (1m, 1h, 1d)

    Returns:
        Subscription key: "BINANCE:BTCUSDT@KLINE_1"
    """
    # Normalize symbol: add EXCHANGE prefix if missing
    if ":" not in symbol:
        exchange = "BINANCE"
        normalized_symbol = symbol
    else:
        exchange, normalized_symbol = symbol.split(":", 1)

    # Normalize interval: ensure TV format (1, 60, D)
    normalized_interval = _normalize_interval(interval)

    return f"{exchange}:{normalized_symbol}@KLINE_{normalized_interval}"


def _normalize_interval(interval: str) -> str:
    """Normalize interval to TV format.

    Binance format (1m, 1h, 1d) -> TV format (1, 60, D)

    Args:
        interval: Interval in Binance or TV format

    Returns:
        Interval in TV format (1, 60, D, W, M)
    """
    if not interval:
        return "1"  # Default to 1 minute

    # If already in TV format (numeric only or D/W/M), return as-is
    if interval.isdigit() or interval in ("D", "W", "M"):
        return interval

    # Convert Binance format to TV format
    binance_to_tv = {
        "1m": "1",
        "3m": "3",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "45m": "45",
        "1h": "60",
        "2h": "120",
        "3h": "180",
        "4h": "240",
        "6h": "360",
        "12h": "720",
        "1d": "D",
        "1w": "W",
        "1M": "M",
    }

    return binance_to_tv.get(interval, interval)
