"""Services module for signal service."""
from .alert_manager import AlertLifecycleManager
from .alert_signal import LoadedAlertConfig
from .constants import REQUIRED_KLINES, TV_INTERVAL_TO_MS
from .kline_cache import _init_kline_cache, _update_kline_cache
from .kline_manager import KlineCacheManager
from .kline_utils import (
    _build_ohlcv_for_trigger_type,
    _convert_time_to_ms,
    _format_kline_time,
    _get_interval_ms,
    _get_previous_period_time,
)
from .kline_validator import (
    _check_kline_continuity,
    _check_kline_continuity_in_dataframe,
    _check_kline_data_validity,
    _check_last_kline_time,
    _validate_cache_for_kline_close,
)
from .signal_service import SignalService
from .subscription_utils import _build_subscription_key, _normalize_interval
from .task_waiter import _wait_for_task_completion
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
    "LoadedAlertConfig",
    # Managers
    "AlertLifecycleManager",
    "KlineCacheManager",
    # Task waiter
    "_wait_for_task_completion",
    # Constants
    "REQUIRED_KLINES",
    "TV_INTERVAL_TO_MS",
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
    "_convert_time_to_ms",
    "_format_kline_time",
    "_build_ohlcv_for_trigger_type",
    "_get_interval_ms",
    "_get_previous_period_time",
    # K-line validator
    "_check_kline_continuity",
    "_check_kline_continuity_in_dataframe",
    "_check_last_kline_time",
    "_check_kline_data_validity",
    "_validate_cache_for_kline_close",
    # K-line cache
    "_update_kline_cache",
    "_init_kline_cache",
]
