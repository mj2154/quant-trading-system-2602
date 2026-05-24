"""Constants used by signal service."""

# Required number of klines for MACD calculation
REQUIRED_KLINES = 350

# Retry delay in seconds for kline fill loop
RETRY_DELAY_SECONDS = 2

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
