"""Services module for signal service."""
from .alert_signal import AlertSignal
from .constants import REQUIRED_KLINES, TV_INTERVAL_TO_MS, TV_TO_BINANCE_INTERVAL
from .kline_cache import _init_kline_cache, _update_kline_cache
from .kline_utils import (
    _build_ohlcv_for_trigger_type,
    _convert_binance_kline_to_standard,
    _convert_klines_to_dataframe,
    _format_kline_time,
    _get_interval_ms,
    _get_previous_period_time,
)
from .kline_validator import (
    _check_kline_continuity,
    _check_kline_data_validity,
    _check_last_kline_time,
)
from .signal_service import SignalService
from .subscription_utils import _build_subscription_key, _normalize_interval
from .trigger_engine import (
    TriggerEngine,
    TriggerState,
    TriggerType,
    create_trigger_state,
    get_trigger_engine,
)

__all__ = [
    # Main service
    "SignalService",
    "AlertSignal",
    # Constants
    "REQUIRED_KLINES",
    "TV_INTERVAL_TO_MS",
    "TV_TO_BINANCE_INTERVAL",
    # Trigger engine
    "TriggerEngine",
    "TriggerState",
    "TriggerType",
    "get_trigger_engine",
    "create_trigger_state",
    # Subscription utilities
    "_build_subscription_key",
    "_normalize_interval",
    # K-line utilities
    "_format_kline_time",
    "_convert_klines_to_dataframe",
    "_build_ohlcv_for_trigger_type",
    "_convert_binance_kline_to_standard",
    "_get_interval_ms",
    "_get_previous_period_time",
    # K-line validator
    "_check_kline_continuity",
    "_check_last_kline_time",
    "_check_kline_data_validity",
    # K-line cache
    "_update_kline_cache",
    "_init_kline_cache",
]
