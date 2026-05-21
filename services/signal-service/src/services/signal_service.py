"""Core signal service logic."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import pandas as pd

from ..db.alert_config_repository import AlertConfigRecord, AlertConfigRepository
from ..db.database import Database
from ..db.realtime_data_repository import RealtimeDataRepository
from ..db.strategy_signals_repository import StrategySignalsRepository
from ..db.tasks_repository import TasksRepository
from ..listener.alert_signal_listener import AlertSignalListener
from ..listener.realtime_update_listener import RealtimeUpdateListener
from ..strategies.base import Strategy
from .alert_signal import LoadedAlertConfig
from .constants import REQUIRED_KLINES, TV_INTERVAL_TO_MS, RETRY_DELAY_SECONDS
from .kline_cache import _init_kline_cache, _update_kline_cache
from .kline_utils import (
    _build_ohlcv_for_trigger_type,
    _format_kline_time,
    _get_interval_ms,
)
from .kline_validator import _check_kline_data_validity
from .subscription_utils import _build_subscription_key
from .trigger_engine import (
    TriggerState,
    TriggerType,
    get_trigger_engine,
)

logger = logging.getLogger(__name__)


def _convert_time_to_ms(time_value: Any) -> int | None:
    """Convert time value to milliseconds integer for comparison."""
    if time_value is None:
        return None
    if hasattr(time_value, 'timestamp'):
        return int(time_value.timestamp() * 1000)
    return int(time_value)


def _validate_cache_for_kline_close(
    cached_klines: pd.DataFrame,
    kline_data: dict[str, Any],
) -> tuple[bool, str]:
    """验证缓存是否包含正确的完结K线.

    Args:
        cached_klines: 缓存的K线DataFrame
        kline_data: 收到的实时K线数据

    Returns:
        (is_valid, reason) - reason 包含详细差异信息
    """
    if cached_klines.empty:
        return False, "cache_empty"

    cached_last_time = cached_klines.iloc[-1]["time"]
    received_time = kline_data.get("k", {}).get("t")

    if received_time is None:
        return False, "received_time_missing"

    cached_ms = _convert_time_to_ms(cached_last_time)
    received_ms = int(received_time)

    if cached_ms != received_ms:
        return False, f"time_mismatch:cached={cached_ms},received={received_ms},diff={abs(cached_ms - received_ms)}ms"

    return True, "ok"


def _check_kline_continuity_in_dataframe(
    df: pd.DataFrame,
    interval_ms: int,
) -> tuple[bool, str]:
    """检查DataFrame中的K线时间连续性.

    Args:
        df: K线DataFrame
        interval_ms: 间隔毫秒数

    Returns:
        (is_valid, reason)
    """
    if len(df) < 2:
        return True, "ok"

    for i in range(1, len(df)):
        prev_time = df.iloc[i-1]["time"]
        curr_time = df.iloc[i]["time"]

        prev_ms = _convert_time_to_ms(prev_time)
        curr_ms = _convert_time_to_ms(curr_time)

        if prev_ms is None or curr_ms is None:
            continue

        diff = curr_ms - prev_ms
        if abs(diff - interval_ms) > 1000:  # 1秒容差
            return False, f"gap_at_index={i},prev={prev_ms},curr={curr_ms},expected_diff={interval_ms}ms"

    return True, "ok"


class SignalService:
    """Signal service that calculates and stores signals from alert configurations.

    This service:
    1. Loads alert configurations from alert_signals table on startup
    2. Creates strategy instances based on alert configuration (strategy_type)
    3. Listens for realtime_update notifications
    4. Uses trigger engine to determine execution timing
    5. Fetches historical klines for indicator calculation
    6. Calculates and stores signals
    """

    def __init__(
        self,
        db: Database,
    ) -> None:
        """Initialize signal service.

        Args:
            db: Database instance.
        """
        self._db = db
        self._realtime_repo = RealtimeDataRepository(db)
        self._alert_repo = AlertConfigRepository(db)
        self._signals_repo = StrategySignalsRepository(db)
        self._tasks_repo = TasksRepository(db)

        # 告警信号实例字典（按 alert_id 索引）
        # key: alert_id (UUID)
        # value: LoadedAlertConfig 实例（包含配置 + 策略实例）
        self._alerts: dict[UUID, LoadedAlertConfig] = {}

        # 按订阅键索引（一个K线数据可能被多个告警使用）
        # key: subscription_key (如 "BINANCE:BTCUSDT@KLINE_60")
        # value: set[alert_id]
        self._alerts_by_key: dict[str, set[UUID]] = {}

        # K线缓存（按订阅键索引，避免每次都查数据库）
        # key: subscription_key
        # value: pd.DataFrame - K线数据，与 backtest fetch_klines 返回格式一致
        #        列名: time, open, high, low, close, volume
        self._kline_cache: dict[str, pd.DataFrame] = {}

        # 补齐锁字典（按订阅键进行互斥控制，防止并发补齐）
        # key: subscription_key
        # value: asyncio.Lock - 每次只能有一个处理流程在该订阅键上
        self._fill_locks: dict[str, asyncio.Lock] = {}

        self._listener: RealtimeUpdateListener | None = None
        self._alert_listener: AlertSignalListener | None = None
        self._connection = None
        self._running = False

    async def start(self) -> None:
        """Start the signal service."""
        logger.info("Starting signal service")
        self._running = True

        # 清理旧的订阅记录，确保与告警配置状态一致
        await self._cleanup_stale_subscriptions()

        # Load alert configurations from alert_signals table
        await self._load_alerts_from_db()

        # Ensure subscriptions exist for configured alerts
        await self._ensure_subscriptions()

        # Create listener for realtime_update notifications
        # Use dedicated connection (not from pool) to maintain LISTEN state
        conn = await self._db.create_dedicated_connection()
        self._connection = conn
        self._listener = RealtimeUpdateListener(
            connection=conn, callback=self._handle_realtime_update
        )
        await self._listener.start()

        # Create listener for alert signal notifications (for dynamic reload)
        self._alert_listener = AlertSignalListener(
            connection=conn,
            on_new=self._handle_alert_new,
            on_update=self._handle_alert_update,
            on_delete=self._handle_alert_delete,
        )
        await self._alert_listener.start()

        logger.info(
            "[STARTUP] Signal service started: alerts=%d, subscription_keys=%s, kline_caches=%s",
            len(self._alerts),
            list(self._alerts_by_key.keys()),
            list(self._kline_cache.keys()),
        )

    async def stop(self) -> None:
        """Stop the signal service."""
        logger.info("Stopping signal service")
        self._running = False

        if self._alert_listener:
            await self._alert_listener.stop()
            self._alert_listener = None

        if self._listener:
            await self._listener.stop()
            if self._connection:
                await self._db.close_dedicated_connection(self._connection)
                self._connection = None

        logger.info("Signal service stopped")

    def _handle_alert_new(self, data: dict[str, Any]) -> None:
        """Handle new alert signal notification.

        Automatically reloads alert configurations when a new alert is created.
        """
        if not self._running:
            return

        alert_id = data.get("id")
        name = data.get("name")
        logger.info("New alert signal detected: id=%s name=%s, reloading...", alert_id, name)

        # Reload alert configurations from database
        asyncio.create_task(self._reload_single_alert(data))

    def _handle_alert_update(self, data: dict[str, Any]) -> None:
        """Handle updated alert signal notification."""
        if not self._running:
            return

        alert_id = data.get("id")
        name = data.get("name")
        logger.info("Alert signal update detected: id=%s name=%s, reloading...", alert_id, name)

        # Reload alert configurations from database
        asyncio.create_task(self._reload_single_alert(data))

    def _handle_alert_delete(self, data: dict[str, Any]) -> None:
        """Handle deleted alert signal notification.

        Uses asyncio.create_task to run async cleanup since AlertSignalListener
        expects synchronous callbacks.
        """
        if not self._running:
            return

        alert_id = data.get("id")
        logger.info("Alert signal delete detected: id=%s, removing...", alert_id)

        # Run async cleanup in background
        asyncio.create_task(self._handle_alert_delete_async(data))

    async def _handle_alert_delete_async(self, data: dict[str, Any]) -> None:
        """Async cleanup logic for deleted alert."""
        alert_id = data.get("id")
        if not alert_id:
            return

        try:
            alert_id_str = str(alert_id)
        except ValueError:
            logger.warning("Invalid alert ID format: %s", alert_id)
            return

        # Remove from memory if exists
        if alert_id_str not in self._alerts:
            return

        old_alert = self._alerts[alert_id_str]
        old_subscription_key = _build_subscription_key(
            old_alert.symbol,
            old_alert.interval
        )

        # Remove from _alerts
        del self._alerts[alert_id_str]

        # Remove from _alerts_by_key
        if old_subscription_key in self._alerts_by_key:
            self._alerts_by_key[old_subscription_key].discard(alert_id_str)
            if not self._alerts_by_key[old_subscription_key]:
                del self._alerts_by_key[old_subscription_key]

        # Cleanup subscription if no other enabled alerts use it
        await self._cleanup_subscription_if_unused(old_subscription_key)

        logger.info("[ALERT_DELETE] Alert deleted: id=%s subscription_key=%s", alert_id, old_subscription_key)

    async def _reload_single_alert(self, data: dict[str, Any]) -> None:
        """Reload a single alert from database notification.

        Simplified logic: Database is single source of truth.
        - Update memory state from DB
        - If enabled: ensure subscription exists
        - If disabled: ensure subscription removed
        """
        alert_id_str = data.get("id")
        if not alert_id_str:
            return

        # Validate UUID format
        try:
            UUID(alert_id_str)
        except ValueError:
            logger.warning("Invalid alert ID format: %s", alert_id_str)
            return

        # Fetch latest state from database
        alert = await self._alert_repo.find_by_id(alert_id_str)
        if not alert:
            # Alert was deleted - remove from memory and cleanup
            logger.info("[ALERT_UPDATE] Alert deleted from DB: %s, cleaning up", alert_id_str)
            if alert_id_str in self._alerts:
                old_alert = self._alerts[alert_id_str]
                old_sub_key = _build_subscription_key(old_alert.symbol, old_alert.interval)

                # Remove from memory indexes
                del self._alerts[alert_id_str]
                if old_sub_key in self._alerts_by_key:
                    self._alerts_by_key[old_sub_key].discard(alert_id_str)
                    if not self._alerts_by_key[old_sub_key]:
                        del self._alerts_by_key[old_sub_key]

                # Remove subscription if no other enabled alerts use it
                await self._cleanup_subscription_if_unused(old_sub_key)
            return

        alert_id = str(alert.id)
        subscription_key = _build_subscription_key(alert.symbol, alert.interval)

        # Create strategy (may raise if strategy_type invalid)
        try:
            trigger_type_enum = TriggerType(alert.trigger_type)
            get_trigger_engine(trigger_type_enum)
        except ValueError:
            logger.warning(
                "Unknown trigger type %s for alert %s, using EACH_KLINE_CLOSE",
                alert.trigger_type,
                alert.name,
            )
            get_trigger_engine(TriggerType.EACH_KLINE_CLOSE)

        strategy = await self._create_strategy(alert)

        # Preserve created_at if updating existing alert
        old_alert = self._alerts.get(alert_id)
        created_at = old_alert.created_at if old_alert else datetime.utcnow()

        # Update memory state
        self._alerts[alert_id] = LoadedAlertConfig(
            alert_id=alert_id,
            name=alert.name,
            strategy_type=alert.strategy_type,
            symbol=alert.symbol,
            interval=alert.interval,
            trigger_type=alert.trigger_type,
            params=alert.params,
            is_enabled=alert.is_enabled,
            created_by=alert.created_by,
            strategy=strategy,
            trigger_state=TriggerState(),
            created_at=created_at,
            updated_at=datetime.utcnow(),
        )

        # Update _alerts_by_key based on current enabled status
        if alert.is_enabled:
            if subscription_key not in self._alerts_by_key:
                self._alerts_by_key[subscription_key] = set()
            self._alerts_by_key[subscription_key].add(alert_id)
        else:
            if subscription_key in self._alerts_by_key:
                self._alerts_by_key[subscription_key].discard(alert_id)
                if not self._alerts_by_key[subscription_key]:
                    del self._alerts_by_key[subscription_key]

        # Manage subscription based on enabled status
        if alert.is_enabled:
            # Ensure subscription exists in DB
            existing = await self._realtime_repo.get_by_subscription_key(subscription_key)
            if existing is None:
                await self._realtime_repo.insert_subscription(
                    subscription_key=subscription_key,
                    data_type="KLINE",
                )
                logger.info("[ALERT_UPDATE] Created subscription: %s", subscription_key)
        else:
            # Ensure subscription removed from DB (if no other enabled alerts use it)
            await self._cleanup_subscription_if_unused(subscription_key)

        logger.info(
            "[ALERT_UPDATE] alert_id=%s name=%s enabled=%s subscription_key=%s",
            alert_id,
            alert.name,
            alert.is_enabled,
            subscription_key,
        )

    async def reload_configs(self) -> None:
        """Reload alert configurations from database.

        This can be called at runtime to pick up new/changed configurations.
        """
        logger.info("Reloading alert configurations")
        old_alerts = set(self._alerts.keys())
        await self._load_alerts_from_db()
        new_alerts = set(self._alerts.keys())

        added = new_alerts - old_alerts
        removed = old_alerts - new_alerts
        if added:
            logger.info("Added %d new alerts", len(added))
        if removed:
            logger.info("Removed %d alerts", len(removed))

    async def _cleanup_stale_subscriptions(self) -> None:
        """Clean up stale subscriptions on startup.

        Removes all signal-service subscriptions from realtime_data table,
        ensuring subscriptions are always consistent with enabled alert configs.
        This handles cases where alerts were disabled/deleted but subscriptions
        weren't properly cleaned up.
        """
        logger.info("Cleaning up stale subscriptions")
        rows = await self._realtime_repo.get_subscriptions_by_subscriber(
            self._realtime_repo.SUBSCRIBER_ID
        )
        if not rows:
            logger.info("No stale subscriptions to clean up")
            return

        cleaned_keys = []
        for row in rows:
            subscription_key = row.subscription_key
            success = await self._realtime_repo.remove_subscription(subscription_key)
            if success:
                cleaned_keys.append(subscription_key)
                logger.info(
                    "Cleaned up stale subscription: %s",
                    subscription_key,
                )
            else:
                logger.warning(
                    "Failed to clean up subscription: %s",
                    subscription_key,
                )

        logger.info(
            "[CLEANUP] Cleaned up %d stale subscriptions: %s",
            len(cleaned_keys),
            cleaned_keys,
        )

    async def _load_alerts_from_db(self) -> None:
        """Load all alert configurations from database.

        All alerts are loaded into _alerts (regardless of is_enabled).
        Only enabled alerts are added to _alerts_by_key for subscriptions.
        """
        # Load ALL alerts from database
        db_alerts = await self._alert_repo.find_all()

        # Clear existing state
        self._alerts.clear()
        self._alerts_by_key.clear()

        for alert in db_alerts:
            alert_id = str(alert.id)

            # Create trigger state for each alert
            try:
                trigger_type_enum = TriggerType(alert.trigger_type)
                get_trigger_engine(trigger_type_enum)
            except ValueError:
                logger.warning(
                    "Unknown trigger type %s for alert %s, using EACH_KLINE_CLOSE",
                    alert.trigger_type,
                    alert.name,
                )
                get_trigger_engine(TriggerType.EACH_KLINE_CLOSE)

            # Create strategy instance
            strategy = await self._create_strategy(alert)

            # Store alert (all alerts, regardless of enabled status)
            self._alerts[alert_id] = LoadedAlertConfig(
                alert_id=alert_id,
                name=alert.name,
                strategy_type=alert.strategy_type,
                symbol=alert.symbol,
                interval=alert.interval,
                trigger_type=alert.trigger_type,
                params=alert.params,
                is_enabled=alert.is_enabled,
                created_by=alert.created_by,
                strategy=strategy,
                trigger_state=TriggerState(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Only add ENABLED alerts to _alerts_by_key (subscriptions)
            if alert.is_enabled:
                subscription_key = _build_subscription_key(alert.symbol, alert.interval)
                if subscription_key not in self._alerts_by_key:
                    self._alerts_by_key[subscription_key] = set()
                self._alerts_by_key[subscription_key].add(alert_id)

        logger.info(
            "[STARTUP] Loaded %d alerts (%d enabled), subscription_keys: %s",
            len(db_alerts),
            len([a for a in db_alerts if a.is_enabled]),
            list(self._alerts_by_key.keys()),
        )

    async def _create_strategy(self, alert: AlertConfigRecord) -> Strategy:
        """Create strategy instance based on alert configuration.

        Uses StrategyRegistry for automatic strategy discovery and instantiation.

        Args:
            alert: Alert configuration record from alert_signals table.

        Returns:
            Strategy instance.

        Raises:
            ValueError: If strategy type is unknown.
        """
        from ..strategies.registry import StrategyRegistry

        strategy_type = alert.strategy_type

        if not strategy_type:
            raise ValueError(f"Alert {alert.name} has no strategy_type configured")

        return StrategyRegistry.create_instance(strategy_type)

    async def _cleanup_subscription_if_unused(self, subscription_key: str) -> None:
        """Remove subscription from DB if no enabled alerts use it.

        Args:
            subscription_key: The subscription key to check and potentially remove.
        """
        # Check if any enabled alert uses this subscription_key
        alert_ids = self._alerts_by_key.get(subscription_key, set())
        has_enabled_alert = any(
            self._alerts[aid].is_enabled
            for aid in alert_ids
            if aid in self._alerts
        )

        if not has_enabled_alert:
            await self._realtime_repo.remove_subscription(subscription_key)
            logger.info(
                "[CLEANUP] Removed unused subscription: %s (no enabled alerts)",
                subscription_key,
            )
        else:
            logger.info(
                "[CLEANUP] Keeping subscription: %s (used by other enabled alerts)",
                subscription_key,
            )

    async def _ensure_subscriptions(self) -> None:
        """Ensure subscriptions exist for all configured alerts and initialize K-line cache."""
        logger.info("Ensuring subscriptions for configured alerts")

        # Track processed subscription keys to avoid duplicate initialization
        processed_keys: set[str] = set()

        for loaded_alert in self._alerts.values():
            if not loaded_alert.is_enabled:
                continue

            # Build subscription key following architecture design
            # Format: {EXCHANGE}:{SYMBOL}@KLINE_{TV_RESOLUTION}
            subscription_key = _build_subscription_key(
                loaded_alert.symbol,
                loaded_alert.interval
            )

            # Check if subscription already exists
            existing = await self._realtime_repo.get_by_subscription_key(subscription_key)
            if existing is None:
                # Create subscription
                await self._realtime_repo.insert_subscription(
                    subscription_key=subscription_key,
                    data_type="KLINE",
                )
                logger.info(
                    "Created subscription: subscription_key=%s alert=%s",
                    subscription_key,
                    loaded_alert.name,
                )

            # Initialize K-line cache if not already done
            if subscription_key not in processed_keys:
                await self._init_kline_cache_for_key(subscription_key)
                processed_keys.add(subscription_key)

    async def _init_kline_cache_for_key(self, subscription_key: str) -> None:
        """Initialize K-line cache for a subscription key.

        Implements three-condition check and fill loop:
        1. Check quantity >= REQUIRED_KLINES
        2. Check kline continuity
        3. Check last kline time = previous period

        If all conditions met, initialize cache and return.
        Otherwise, enter fill loop until task succeeds.

        Args:
            subscription_key: The subscription key to initialize cache for.
        """
        # Extract symbol and interval from subscription key
        # Format: BINANCE:BTCUSDT@KLINE_60
        if "@" not in subscription_key:
            logger.error("Invalid subscription key format: %s", subscription_key)
            return

        symbol_with_prefix = subscription_key.split("@")[0]
        interval = subscription_key.split("@")[1].replace("KLINE_", "")
        symbol = symbol_with_prefix

        # First check: fetch and validate
        history = await self._realtime_repo.get_klines_history(
            symbol=symbol,
            interval=interval,
            limit=REQUIRED_KLINES,
        )

        # Check three conditions
        is_valid, reason = _check_kline_data_validity(history, interval, REQUIRED_KLINES)

        if is_valid:
            # All conditions met, initialize cache
            await self._do_init_kline_cache(subscription_key, history)
            return

        # Conditions not met, enter fill loop
        logger.warning(
            "K-line data validation failed: subscription_key=%s reason=%s, entering fill loop",
            subscription_key,
            reason,
        )

        await self._fill_kline_data(subscription_key, symbol, interval)

    async def _fill_kline_data(self, subscription_key: str, symbol: str, interval: str) -> None:
        """Fill kline data by creating tasks and waiting for completion.

        Loop until task succeeds (infinite loop as per design):
        1. Create task: get_klines, limit=1000
        2. Listen for task notification (5s timeout)
        3. On failure/timeout: sleep 2s, retry
        4. On success: re-query data, initialize cache

        Note: Design requires infinite loop until success, no max_retries limit.
        Connection is reused across retries to avoid overhead of creating new connections.

        Args:
            subscription_key: The subscription key.
            symbol: Trading pair symbol.
            interval: TV format interval.
        """
        retry_count = 0

        # Create a dedicated connection for the entire fill loop
        # This avoids the overhead of creating new connections on each retry
        conn = await self._db.create_dedicated_connection()

        try:
            while True:
                retry_count += 1

                # Create task
                logger.info(
                    "Creating kline fill task: subscription_key=%s retry=%d",
                    subscription_key,
                    retry_count,
                )

                task_id = await self._tasks_repo.create_task(
                    task_type="get_klines",
                    payload={
                        "symbol": symbol,
                        "interval": interval,
                        "limit": 1000,
                    },
                )

                # Wait for task completion with 5s timeout (reusing connection)
                task_status = await self._wait_for_task_completion_with_conn(
                    conn, task_id, timeout=5
                )

                if task_status == "completed":
                    # Task succeeded, re-query and initialize
                    logger.info(
                        "Kline fill task completed: subscription_key=%s retry=%d",
                        subscription_key,
                        retry_count,
                    )

                    # DEBUG: Query history data after task completed
                    history = await self._realtime_repo.get_klines_history(
                        symbol=symbol,
                        interval=interval,
                        limit=REQUIRED_KLINES,
                    )
                    logger.info(
                        "_fill_kline_data: Queried history: subscription_key=%s symbol=%s interval=%s history_count=%d",
                        subscription_key,
                        symbol,
                        interval,
                        len(history),
                    )

                    await self._do_init_kline_cache(subscription_key, history)
                    return

                # Task failed or timeout, retry after sleep
                logger.warning(
                    "Kline fill task failed/timeout: subscription_key=%s status=%s retry=%d",
                    subscription_key,
                    task_status,
                    retry_count,
                )

                await asyncio.sleep(RETRY_DELAY_SECONDS)

            # Note: This should never be reached as the loop is infinite per design
            logger.error(
                "Kline fill loop exited unexpectedly: subscription_key=%s retry_count=%d",
                subscription_key,
                retry_count,
            )
        finally:
            # Always close the dedicated connection when done
            await self._db.close_dedicated_connection(conn)
            logger.debug("Closed dedicated connection for kline fill: %s", subscription_key)

    async def _wait_for_task_completion(self, task_id: int, timeout: int) -> str | None:
        """Wait for task completion via notification or timeout.

        Uses PostgreSQL NOTIFY/LISTEN mechanism:
        - Listen for task_completed and task_failed notifications
        - 5 second timeout
        - On timeout, query database to check if task is stuck

        Args:
            task_id: Task ID to wait for.
            timeout: Timeout in seconds.

        Returns:
            Task status: "completed", "failed", or None on timeout.
        """
        # Create a dedicated connection for listening to task notifications
        conn = await self._db.create_dedicated_connection()

        try:
            # Set up event to signal when notification received
            completed_event = asyncio.Event()
            failed_event = asyncio.Event()

            async def handle_completed(
                connection: Any, pid: int, channel: str, payload: str
            ) -> None:
                """Handle task_completed notification."""
                try:
                    data = json.loads(payload)
                    if data.get("id") == task_id:
                        completed_event.set()
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse task_completed payload: %s", e)
                except Exception as e:
                    logger.error("Unexpected error in task_completed handler: %s", e)

            async def handle_failed(
                connection: Any, pid: int, channel: str, payload: str
            ) -> None:
                """Handle task_failed notification."""
                try:
                    data = json.loads(payload)
                    if data.get("id") == task_id:
                        failed_event.set()
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse task_failed payload: %s", e)
                except Exception as e:
                    logger.error("Unexpected error in task_failed handler: %s", e)

            # Register listeners
            await conn.add_listener("task_completed", handle_completed)
            await conn.add_listener("task_failed", handle_failed)

            # Wait for either notification with timeout
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(completed_event.wait()),
                    asyncio.create_task(failed_event.wait()),
                ],
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            # Check which event was set
            if completed_event.is_set():
                return "completed"
            if failed_event.is_set():
                return "failed"

            # Timeout - query database to check status
            status = await self._tasks_repo.get_task_status(task_id)
            logger.debug(
                "Task wait timeout: task_id=%s timeout=%ds status=%s",
                task_id,
                timeout,
                status,
            )

            # If still processing after timeout, treat as stuck
            if status == "processing":
                return None

            return status

        except Exception as e:
            logger.error(
                "Error waiting for task completion: task_id=%s error=%s",
                task_id,
                e,
            )
            return None
        finally:
            # Clean up connection
            await self._db.close_dedicated_connection(conn)

    async def _wait_for_task_completion_with_conn(
        self,
        conn: Any,
        task_id: int,
        timeout: int,
    ) -> str | None:
        """Wait for task completion via notification or timeout, using provided connection.

        This method reuses the provided connection instead of creating a new one,
        which is more efficient when called in a loop (e.g., kline fill loop).

        Uses PostgreSQL NOTIFY/LISTEN mechanism:
        - Listen for task_completed and task_failed notifications
        - 5 second timeout
        - On timeout, query database to check if task is stuck

        Args:
            conn: Existing dedicated database connection to use.
            task_id: Task ID to wait for.
            timeout: Timeout in seconds.

        Returns:
            Task status: "completed", "failed", or None on timeout.
        """
        # Set up event to signal when notification received
        completed_event = asyncio.Event()
        failed_event = asyncio.Event()

        async def handle_completed(
            connection: Any, pid: int, channel: str, payload: str
        ) -> None:
            """Handle task_completed notification."""
            try:
                data = json.loads(payload)
                if data.get("id") == task_id:
                    completed_event.set()
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse task_completed payload: %s", e)
            except Exception as e:
                logger.error("Unexpected error in task_completed handler: %s", e)

        async def handle_failed(
            connection: Any, pid: int, channel: str, payload: str
        ) -> None:
            """Handle task_failed notification."""
            try:
                data = json.loads(payload)
                if data.get("id") == task_id:
                    failed_event.set()
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse task_failed payload: %s", e)
            except Exception as e:
                logger.error("Unexpected error in task_failed handler: %s", e)

        # Register listeners on the provided connection
        await conn.add_listener("task_completed", handle_completed)
        await conn.add_listener("task_failed", handle_failed)

        try:
            # Wait for either notification with timeout
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(completed_event.wait()),
                    asyncio.create_task(failed_event.wait()),
                ],
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            # Check which event was set
            if completed_event.is_set():
                return "completed"
            if failed_event.is_set():
                return "failed"

            # Timeout - query database to check status
            status = await self._tasks_repo.get_task_status(task_id)
            logger.debug(
                "Task wait timeout: task_id=%s timeout=%ds status=%s",
                task_id,
                timeout,
                status,
            )

            # If still processing after timeout, treat as stuck
            if status == "processing":
                return None

            return status

        except Exception as e:
            logger.error(
                "Error waiting for task completion: task_id=%s error=%s",
                task_id,
                e,
            )
            return None
        finally:
            # Clean up listeners but DON'T close the connection (caller manages it)
            await conn.remove_listener("task_completed", handle_completed)
            await conn.remove_listener("task_failed", handle_failed)

    async def _do_init_kline_cache(
        self,
        subscription_key: str,
        history: list[dict[str, Any]],
    ) -> None:
        """Initialize kline cache with given history data.

        Args:
            subscription_key: The subscription key.
            history: List of kline records from database.
        """
        # Initialize cache
        _init_kline_cache(
            cache=self._kline_cache,
            subscription_key=subscription_key,
            history=history,
            required_klines=REQUIRED_KLINES,
        )

        cached_klines = self._kline_cache.get(subscription_key, pd.DataFrame())
        cached_count = len(cached_klines)

        # Get time range for debugging
        first_time_raw = cached_klines.iloc[0]["time"] if len(cached_klines) > 0 else None
        last_time_raw = cached_klines.iloc[-1]["time"] if len(cached_klines) > 0 else None

        # Format time to China Standard Time (UTC+8)
        first_time = _format_kline_time(first_time_raw)
        last_time = _format_kline_time(last_time_raw)

        logger.info(
            "Initialized K-line cache: subscription_key=%s klines=%d time_range=[%s -> %s]",
            subscription_key,
            cached_count,
            first_time,
            last_time,
        )

    def _handle_realtime_update(self, notification: dict[str, Any]) -> None:
        """Handle realtime_update notification.

        Args:
            notification: The notification payload from pg_notify.
        """
        if not self._running:
            return

        # Schedule the async handler
        asyncio.create_task(self._process_realtime_update(notification))

    async def _process_realtime_update(self, notification: dict[str, Any]) -> None:
        """Process a realtime_update notification.

        处理流程（按照设计文档 8.5.5.2）：
        1. 检查该订阅键是否正在补齐（是否有锁）
        2. 如果正在补齐：记录日志，忽略本次更新，返回
        3. 如果没有锁：获取锁后执行处理流程
        4. 初始化缓存（如需要）
        5. 【先检测】连续性检测
        6. 【关键】如果需要补齐，同步等待补齐完成
        7. 【后更新】更新K线缓存
        8. 执行策略计算
        9. 释放锁

        Args:
            notification: The notification payload.
        """
        try:
            data = notification.get("data", {})
            subscription_key = data.get("subscription_key")
            data_type = data.get("data_type")
            kline_data = data.get("data")
            event_time_str = data.get("event_time")

            # Only process KLINE data
            if data_type != "KLINE":
                return

            # Check if there are alerts using this subscription key
            alert_ids = self._alerts_by_key.get(subscription_key, set())
            if not alert_ids:
                # No alerts need this subscription key
                return

            # ==== 【第一步：检查是否正在补齐】====
            # 如果该订阅键正在补齐中（锁已被占用），忽略本次更新，避免并发问题
            existing_lock = self._fill_locks.get(subscription_key)
            if existing_lock and existing_lock.locked():
                logger.debug(
                    "Fill in progress, skipping update: subscription_key=%s",
                    subscription_key
                )
                return

            # 获取或创建锁
            if subscription_key not in self._fill_locks:
                self._fill_locks[subscription_key] = asyncio.Lock()

            async with self._fill_locks[subscription_key]:
                # ==== 以下是锁内的处理逻辑 ====

                # Get is_closed status from kline data
                # Binance API uses "x" field in "k" object to indicate if kline is closed
                if kline_data:
                    k_data = kline_data.get("k", {})
                    is_closed = k_data.get("x", False)
                else:
                    is_closed = False

                # Get new_time for continuity detection
                k_info = kline_data.get("k", kline_data) if kline_data else {}
                new_time = k_info.get("t") if k_info else None

                # If cache not initialized, initialize it first
                if subscription_key not in self._kline_cache:
                    await self._init_kline_cache_for_key(subscription_key)

                # Get current cached klines
                cached_klines = self._kline_cache.get(subscription_key, pd.DataFrame())

                # ==== 【第二步：运行中数据连续性检测】====
                # 先检测是否需要补齐，再更新缓存
                needs_fill = False
                if len(cached_klines) >= 1 and new_time:
                    # Parse interval from subscription_key (format: BINANCE:BTCUSDT@KLINE_60)
                    try:
                        interval = subscription_key.split("@KLINE_")[-1]
                    except (ValueError, IndexError):
                        interval = "1"  # Default 1 minute

                    # Get cache last kline time
                    cache_last_time = cached_klines.iloc[-1]["time"]

                    if cache_last_time:
                        interval_ms = TV_INTERVAL_TO_MS.get(interval, 60000)
                        gap = new_time - cache_last_time

                        # 判断场景：
                        # - gap == 0: 时间一致，更新该K线
                        # - gap == interval_ms: 间隔1个周期，新增K线
                        # - gap > interval_ms * 1.5: 数据不连续，需要补齐
                        # - 其他: 正常更新，无需补齐

                        if gap > interval_ms * 1.5:
                            # 数据不连续，需要补齐
                            needs_fill = True
                            # [DEBUG] 显示格式化的时间便于调试
                            cache_time_str = _format_kline_time(cache_last_time)
                            new_time_str = _format_kline_time(new_time)
                            logger.warning(
                                "[DEBUG_GAP] Detected kline gap: subscription_key=%s "
                                "cache_last=%d (%s) new=%d (%s) gap=%dms interval=%s (%.1fx) - NEEDS FILL",
                                subscription_key, cache_last_time, cache_time_str, new_time, new_time_str,
                                gap, interval, gap / interval_ms
                            )

                # ==== 【第三步：如果需要补齐，同步等待补齐完成】====
                # 解析 symbol 和 interval（与启动时保持一致）
                symbol_with_prefix = subscription_key.split("@")[0]
                symbol = symbol_with_prefix
                interval = subscription_key.split("@")[1].replace("KLINE_", "")

                if needs_fill:
                    # 【关键】必须等待补齐程序执行完毕并建立新缓存后，才能进入后续流程
                    logger.info(
                        "Starting synchronous kline fill: subscription_key=%s symbol=%s interval=%s",
                        subscription_key, symbol, interval
                    )
                    await self._fill_kline_data(subscription_key, symbol, interval)
                    logger.info(
                        "Kline fill completed, cache rebuilt: subscription_key=%s",
                        subscription_key
                    )

                    # ========== [DEBUG] 补齐完成后显示数据时间范围 ==========
                    cached_klines = self._kline_cache.get(subscription_key, pd.DataFrame())
                    if len(cached_klines) > 0:
                        first_time = cached_klines.iloc[0]["time"]
                        last_time = cached_klines.iloc[-1]["time"]
                        first_time_str = _format_kline_time(first_time)
                        last_time_str = _format_kline_time(last_time)
                        logger.info(
                            "[DEBUG_FILL] After fill - subscription_key=%s klines=%d time_range=[%s -> %s]",
                            subscription_key, len(cached_klines), first_time_str, last_time_str
                        )
                    else:
                        logger.warning(
                            "[DEBUG_FILL] After fill - subscription_key=%s: cache is empty!",
                            subscription_key
                        )

                    # 补齐完成后，重新获取缓存
                    cached_klines = self._kline_cache.get(subscription_key, pd.DataFrame())

                # ==== 【第四步：更新K线缓存】====
                # 在连续性检测之后更新缓存（无论是否进行了补齐）
                _update_kline_cache(
                    cache=self._kline_cache,
                    subscription_key=subscription_key,
                    kline_data=kline_data,
                    required_klines=REQUIRED_KLINES,
                )

                # Get updated cached klines
                cached_klines = self._kline_cache.get(subscription_key, pd.DataFrame())

                # ==== 【第五步：检查K线数量并执行策略计算】====
                # Check if cached klines are sufficient for signal calculation
                if len(cached_klines) < REQUIRED_KLINES:
                    logger.warning(
                        "Insufficient cached klines: subscription_key=%s got=%d need=%d",
                        subscription_key,
                        len(cached_klines),
                        REQUIRED_KLINES,
                    )
                    return

                # Parse event time
                try:
                    event_time = datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    event_time = datetime.utcnow()

                # Process each alert that uses this subscription key
                for alert_id in alert_ids:
                    await self._process_alert_signal(
                        alert_id=alert_id,
                        subscription_key=subscription_key,
                        kline_data=kline_data,
                        cached_klines=cached_klines,
                        is_closed=is_closed,
                        event_time=event_time,
                    )

            # ==== 锁自动释放 ====

        except Exception as e:
            logger.error(
                "Failed to process realtime update: %s notification=%s",
                str(e),
                json.dumps(notification)[:500],
                exc_info=True,
            )

    async def _process_alert_signal(
        self,
        alert_id: UUID,
        subscription_key: str,
        kline_data: dict[str, Any],
        cached_klines: pd.DataFrame,
        is_closed: bool,
        event_time: datetime,
    ) -> None:
        """Process signal calculation for a single alert.

        Args:
            alert_id: The alert ID to process.
            subscription_key: The subscription key.
            kline_data: The current K-line data.
            cached_klines: The cached K-lines as DataFrame.
            is_closed: Whether the current K-line is closed.
            event_time: The event time.
        """
        loaded_alert = self._alerts.get(alert_id)
        if not loaded_alert or not loaded_alert.is_enabled:
            return

        trigger_type = loaded_alert.trigger_type

        # DEBUG: Log kline time range, closed status, and trigger type
        first_kline_time_raw = cached_klines.iloc[0]["time"] if len(cached_klines) > 0 else None
        last_kline_time_raw = cached_klines.iloc[-1]["time"] if len(cached_klines) > 0 else None
        current_kline_time_raw = kline_data.get("k", {}).get("t") if kline_data else None

        # Format time to China Standard Time (UTC+8)
        first_kline_time = _format_kline_time(first_kline_time_raw)
        last_kline_time = _format_kline_time(last_kline_time_raw)
        current_kline_time = _format_kline_time(current_kline_time_raw)

        logger.debug(
            "[DEBUG_SIGNAL] alert=%s trigger_type=%s is_closed=%s "
            "kline_range=[%s -> %s] current_kline_time=%s",
            loaded_alert.name,
            trigger_type,
            is_closed,
            first_kline_time,
            last_kline_time,
            current_kline_time,
        )

        # Determine if we should calculate based on trigger type
        should_calculate = False
        if trigger_type == "each_kline":
            # Always calculate on each K-line update
            should_calculate = True
        elif trigger_type == "each_kline_close":
            # Only calculate when K-line is closed
            should_calculate = is_closed
        elif trigger_type == "each_minute":
            # TODO: Implement minute-based triggering
            should_calculate = True
        else:
            # Default to each_kline_close behavior
            should_calculate = is_closed

        if not should_calculate:
            return

        # Check trigger engine
        try:
            trigger_type_enum = TriggerType(loaded_alert.trigger_type)
            trigger_engine = get_trigger_engine(trigger_type_enum)
            should_execute, new_trigger_state = trigger_engine.should_execute(
                loaded_alert.trigger_state,
                kline_data or {},
                event_time,
            )

            if not should_execute:
                # Update trigger state but don't calculate
                self._alerts[alert_id] = LoadedAlertConfig(
                    alert_id=loaded_alert.alert_id,
                    name=loaded_alert.name,
                    strategy_type=loaded_alert.strategy_type,
                    symbol=loaded_alert.symbol,
                    interval=loaded_alert.interval,
                    trigger_type=loaded_alert.trigger_type,
                    params=loaded_alert.params,
                    is_enabled=loaded_alert.is_enabled,
                    created_by=loaded_alert.created_by,
                    strategy=loaded_alert.strategy,
                    trigger_state=new_trigger_state,
                    created_at=loaded_alert.created_at,
                    updated_at=datetime.utcnow(),
                )
                return
        except ValueError as e:
            logger.warning("Invalid trigger type: %s", e)
            return

        # ========================================
        # 【新增】对于 each_kline_close，验证缓存正确性
        # ========================================
        if trigger_type == "each_kline_close":
            cache_valid, cache_reason = _validate_cache_for_kline_close(cached_klines, kline_data)

            if not cache_valid:
                cached_last_time = cached_klines.iloc[-1]["time"] if not cached_klines.empty else "N/A"
                cached_last_close = cached_klines.iloc[-1]["close"] if not cached_klines.empty else "N/A"
                received_time = kline_data.get("k", {}).get("t")
                logger.warning(
                    "[CACHE_VALIDATION_FAILED] alert=%s reason=%s "
                    "cached_last_time=%s cached_last_close=%s received_time=%s, attempting cache repair",
                    loaded_alert.name,
                    cache_reason,
                    cached_last_time,
                    cached_last_close,
                    received_time,
                )

                # 尝试重新初始化缓存
                await self._init_kline_cache_for_key(subscription_key)
                repaired_cached_klines = self._kline_cache.get(subscription_key, pd.DataFrame())

                # 再次验证
                cache_valid, cache_reason = _validate_cache_for_kline_close(repaired_cached_klines, kline_data)

                if not cache_valid:
                    cached_last_time = repaired_cached_klines.iloc[-1]["time"] if not repaired_cached_klines.empty else "N/A"
                    cached_last_close = repaired_cached_klines.iloc[-1]["close"] if not repaired_cached_klines.empty else "N/A"
                    received_time = kline_data.get("k", {}).get("t")
                    logger.error(
                        "[CACHE_VALIDATION_FATAL] alert=%s cache_repair_failed reason=%s "
                        "cached_last_time=%s cached_last_close=%s received_time=%s",
                        loaded_alert.name,
                        cache_reason,
                        cached_last_time,
                        cached_last_close,
                        received_time,
                    )
                    return  # 跳过本次计算

                # 修复成功，使用修复后的缓存
                cached_klines = repaired_cached_klines
                logger.info(
                    "[CACHE_REPAIRED] alert=%s subscription_key=%s",
                    loaded_alert.name,
                    subscription_key,
                )

        # ========================================
        # 【新增】验证数量和连续性
        # ========================================
        interval_ms = _get_interval_ms(loaded_alert.interval)

        # 数量检查
        if len(cached_klines) < REQUIRED_KLINES:
            last_time = cached_klines.iloc[-1]["time"] if not cached_klines.empty else "N/A"
            last_close = cached_klines.iloc[-1]["close"] if not cached_klines.empty else "N/A"
            logger.error(
                "[INSUFFICIENT_KLINES] alert=%s got=%d need=%d "
                "cached_last_time=%s cached_last_close=%s",
                loaded_alert.name,
                len(cached_klines),
                REQUIRED_KLINES,
                last_time,
                last_close,
            )
            return

        # 连续性检查
        continuity_valid, continuity_reason = _check_kline_continuity_in_dataframe(cached_klines, interval_ms)
        if not continuity_valid:
            logger.warning(
                "[KLINE_CONTINUITY_FAILED] alert=%s reason=%s, attempting repair",
                loaded_alert.name,
                continuity_reason,
            )
            # 同样尝试重新初始化缓存
            await self._init_kline_cache_for_key(subscription_key)
            repaired_cached_klines = self._kline_cache.get(subscription_key, pd.DataFrame())

            continuity_valid, continuity_reason = _check_kline_continuity_in_dataframe(repaired_cached_klines, interval_ms)
            if not continuity_valid:
                last_time = repaired_cached_klines.iloc[-1]["time"] if not repaired_cached_klines.empty else "N/A"
                last_close = repaired_cached_klines.iloc[-1]["close"] if not repaired_cached_klines.empty else "N/A"
                received_time = kline_data.get("k", {}).get("t")
                logger.error(
                    "[KLINE_CONTINUITY_FATAL] alert=%s reason=%s "
                    "cached_last_time=%s cached_last_close=%s received_time=%s",
                    loaded_alert.name,
                    continuity_reason,
                    last_time,
                    last_close,
                    received_time,
                )
                return

            cached_klines = repaired_cached_klines
            logger.info(
                "[CACHE_REPAIRED] alert=%s subscription_key=%s (continuity repair)",
                loaded_alert.name,
                subscription_key,
            )

        # Build ohlcv DataFrame based on trigger type
        ohlcv = _build_ohlcv_for_trigger_type(
            history=cached_klines,
            current_kline=kline_data if not is_closed else None,
            trigger_type=trigger_type,
        )

        # DEBUG: Log ohlcv data range
        if len(ohlcv) > 0:
            first_time = ohlcv.index[0] if hasattr(ohlcv.index[0], 'isoformat') else str(ohlcv.index[0])
            last_time = ohlcv.index[-1] if hasattr(ohlcv.index[-1], 'isoformat') else str(ohlcv.index[-1])
            logger.debug(
                "[DEBUG_OHLCV] alert=%s ohlcv_len=%d range=[%s -> %s]",
                loaded_alert.name,
                len(ohlcv),
                first_time,
                last_time,
            )

        # Check if we have enough klines
        if len(ohlcv) < REQUIRED_KLINES:
            logger.warning(
                "Insufficient klines for signal calculation: alert=%s got=%d need=%d",
                loaded_alert.name,
                len(ohlcv),
                REQUIRED_KLINES,
            )
            return


        # ========================================
        # 【新增】打印计算前的详细信息日志
        # ========================================
        last_kline = ohlcv.iloc[-1]
        last_open_time_raw = last_kline["time"]
        last_open_time = _format_kline_time(last_open_time_raw)
        last_close_price = last_kline["close"]

        logger.info(
            "[CALC_START] alert=%s strategy=%s trigger_type=%s "
            "last_kline_open_time=%s last_kline_close_price=%s "
            "ohlcv_count=%d symbol=%s interval=%s",
            loaded_alert.name,
            loaded_alert.strategy_type,
            trigger_type,
            last_open_time,
            last_close_price,
            len(ohlcv),
            loaded_alert.symbol,
            loaded_alert.interval,
        )

        # Calculate signal with ohlcv DataFrame
        output = loaded_alert.calculate(ohlcv)

        # Skip writing if signal_value is None (no signal)
        if output.signal_value is None:
            logger.debug(
                "[DEBUG_SKIP] alert=%s signal_reason=%s (no signal generated)",
                loaded_alert.name,
                output.signal_reason,
            )
            return

        # Write signal to database
        await self._signals_repo.insert_signal(
            alert_id=str(alert_id),
            name=loaded_alert.name,
            strategy_type=loaded_alert.strategy_type,
            symbol=loaded_alert.symbol,
            interval=loaded_alert.interval,
            signal_value=output.signal_value,
            signal_reason=output.signal_reason,
            trigger_type=loaded_alert.trigger_type,
            source_subscription_key=subscription_key,
            metadata={
                "processed_at": datetime.utcnow().isoformat(),
            },
            created_by=loaded_alert.created_by,
        )

        logger.info(
            "Signal computed and saved: alert=%s symbol=%s interval=%s signal_value=%s reason=%s",
            loaded_alert.name,
            loaded_alert.symbol,
            loaded_alert.interval,
            output.signal_value,
            output.signal_reason,
        )

        # Update trigger state
        self._alerts[alert_id] = LoadedAlertConfig(
            alert_id=loaded_alert.alert_id,
            name=loaded_alert.name,
            strategy_type=loaded_alert.strategy_type,
            symbol=loaded_alert.symbol,
            interval=loaded_alert.interval,
            trigger_type=loaded_alert.trigger_type,
            params=loaded_alert.params,
            is_enabled=loaded_alert.is_enabled,
            created_by=loaded_alert.created_by,
            strategy=loaded_alert.strategy,
            trigger_state=new_trigger_state,
            created_at=loaded_alert.created_at,
            updated_at=datetime.utcnow(),
        )
