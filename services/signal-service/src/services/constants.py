"""Constants used by signal service."""

# Required number of klines for MACD calculation
REQUIRED_KLINES = 280

# TV resolution to Binance interval format mapping
TV_TO_BINANCE_INTERVAL = {
    "1": "1m",
    "3": "3m",
    "5": "5m",
    "15": "15m",
    "30": "30m",
    "45": "45m",
    "60": "1h",
    "120": "2h",
    "180": "3h",
    "240": "4h",
    "360": "6h",
    "720": "12h",
    "D": "1d",
    "W": "1w",
    "M": "1M",
}

# TV interval to milliseconds mapping
TV_INTERVAL_TO_MS = {
    "1": 1 * 60 * 1000,
    "3": 3 * 60 * 1000,
    "5": 5 * 60 * 1000,
    "15": 15 * 60 * 1000,
    "30": 30 * 60 * 1000,
    "45": 45 * 60 * 1000,
    "60": 60 * 60 * 1000,
    "120": 120 * 60 * 1000,
    "180": 180 * 60 * 1000,
    "240": 240 * 60 * 1000,
    "360": 360 * 60 * 1000,
    "720": 720 * 60 * 1000,
    "D": 24 * 60 * 60 * 1000,
    "W": 7 * 24 * 60 * 60 * 1000,
    "M": 30 * 24 * 60 * 60 * 1000,
}
