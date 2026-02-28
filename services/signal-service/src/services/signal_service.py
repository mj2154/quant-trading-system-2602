"""Core signal service logic.

This module contains the main signal service that:
1. Loads alert configurations from alert_signals table
2. Listens for realtime.update notifications
3. Uses trigger engine to determine when to execute strategies
4. Fetches historical klines for indicator calculation
5. Calculates strategy signals
6. Writes signals to the database
"""

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
from .alert_signal import AlertSignal
from .constants import REQUIRED_KLINES, TV_INTERVAL_TO_MS
from .kline_cache import _init_kline_cache, _update_kline_cache
from .kline_utils import (
    _build_ohlcv_for_trigger_type,
    _convert_binance_kline_to_standard,
    _convert_klines_to_dataframe,
    _format_kline_time,
    _get_interval_ms,
    _get_previous_period_time,
)
from .kline_validator import _check_kline_data_validity
from .subscription_utils import _build_subscription_key
from .trigger_engine import (
    TriggerState,
    TriggerType,
    get_trigger_engine,
)


logger = logging.getLogger(__name__)


class SignalService:
    """Signal service that calculates and stores signals from alert configurations.

    This service:
    1. Loads alert configurations from alert_signals table on startup
    2. Creates strategy instances based on alert configuration (strategy_type)
    3. Listens for realtime.update notifications
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
        # value: AlertSignal 实例（包含配置 + 策略实例）
        self._alerts: dict[UUID, AlertSignal] = {}

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

        # Load alert configurations from alert_signals table
        await self._load_alerts_from_db()

        # Ensure subscriptions exist for configured alerts
        await self._ensure_subscriptions()

        # Create listener for realtime.update notifications
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

        # Remove the alert from memory and cleanup indexes
        try:
            alert_uuid = UUID(alert_id)
            if alert_uuid in self._alerts:
                # Get old subscription_key before deletion
                old_alert = self._alerts[alert_uuid]
                old_subscription_key = _build_subscription_key(
                    old_alert.symbol,
                    old_alert.interval
                )

                # Remove from _alerts
                del self._alerts[alert_uuid]
                logger.info("[ALERT_DELETE] Alert removed from _alerts: id=%s", alert_id)

                # Cleanup _alerts_by_key index
                if old_subscription_key in self._alerts_by_key:
                    self._alerts_by_key[old_subscription_key].discard(alert_uuid)
                    if not self._alerts_by_key[old_subscription_key]:
                        del self._alerts_by_key[old_subscription_key]
                    logger.info(
                        "[ALERT_DELETE] Removed from _alerts_by_key: subscription_key=%s "
                        "(remaining keys: %s)",
                        old_subscription_key,
                        list(self._alerts_by_key.keys()),
                    )

                # Cleanup subscription in database (if no other enabled alerts using this key)
                other_enabled_alerts_using_key = False
                for key, alert_ids in self._alerts_by_key.items():
                    if key == old_subscription_key:
                        for other_id in alert_ids:
                            if str(other_id) in self._alerts:
                                other_alert = self._alerts[str(other_id)]
                                if other_alert.is_enabled:
                                    other_enabled_alerts_using_key = True
                                    break
                        break

                if not other_enabled_alerts_using_key:
                    await self._realtime_repo.remove_subscription(old_subscription_key)
                    logger.info("[ALERT_DELETE] Subscription removed: %s", old_subscription_key)
                else:
                    logger.info(
                        "[ALERT_DELETE] Other enabled alerts using subscription_key=%s, keeping subscription",
                        old_subscription_key,
                    )

                # Cleanup _kline_cache (optional, as it may be used by other alerts)
                # Note: Don't delete _kline_cache here as it may be shared
        except ValueError:
            logger.warning("Invalid alert ID format: %s", alert_id)

    async def _reload_single_alert(self, data: dict[str, Any]) -> None:
        """Reload a single alert from database notification.

        Handles both new alerts and updates to existing alerts.
        When interval or symbol changes, cleans up old subscription_key indexes.
        """
        alert_id_str = data.get("id")
        if not alert_id_str:
            return

        # Validate UUID format
        try:
            alert_uuid = UUID(alert_id_str)
        except ValueError:
            logger.warning("Invalid alert ID format: %s", alert_id_str)
            return

        # ========== Step 1: Get old config (for cleanup) ==========
        # Use string as key to match storage format
        alert_id_key = str(alert_uuid)

        old_alert = self._alerts.get(alert_id_key)

        old_subscription_key = None
        if old_alert:
            old_subscription_key = _build_subscription_key(
                old_alert.symbol,
                old_alert.interval
            )

        # ========== Step 2: Fetch new config from database ==========
        alert = await self._alert_repo.find_by_id(alert_id_str)
        if not alert:
            logger.warning("Alert not found in database: %s", alert_id_str)
            return

        # Use string as key for consistency
        alert_id = str(alert.id)

        # ========== Step 2.5: Check if is_enabled changed ==========
        # Handle subscription based on is_enabled state change
        # New subscription_key is used for both old and new checks
        new_subscription_key = _build_subscription_key(alert.symbol, alert.interval)

        old_is_enabled = old_alert.is_enabled if old_alert else None
        new_is_enabled = alert.is_enabled

        # If is_enabled changed from true to false, remove subscription
        if old_is_enabled is True and new_is_enabled is False:
            logger.info(
                "[ALERT_UPDATE] is_enabled changed: true -> false, removing subscription: "
                "alert_id=%s subscription_key=%s",
                alert_id,
                new_subscription_key,
            )
            # Check if other alerts are using this subscription_key
            other_alerts_using_key = False
            for key, alert_ids in self._alerts_by_key.items():
                if key == new_subscription_key and len(alert_ids) > 0:
                    # Check if there are other ENABLED alerts
                    for other_id in alert_ids:
                        if other_id != alert_id and str(other_id) in self._alerts:
                            other_alert = self._alerts[str(other_id)]
                            if other_alert.is_enabled:
                                other_alerts_using_key = True
                                break
                    break

            if not other_alerts_using_key:
                await self._realtime_repo.remove_subscription(new_subscription_key)
                logger.info("[ALERT_UPDATE] Subscription removed: %s", new_subscription_key)
            else:
                logger.info(
                    "[ALERT_UPDATE] Other enabled alerts using subscription_key=%s, keeping subscription",
                    new_subscription_key,
                )

        # ========== Step 3: Check if subscription_key changed ==========

        # If subscription_key changed, cleanup old indexes
        if old_subscription_key and old_subscription_key != new_subscription_key:
            logger.info(
                "[ALERT_UPDATE] subscription_key changed: %s -> %s (alert_id=%s)",
                old_subscription_key,
                new_subscription_key,
                alert_id_key,
            )

            # Remove from old _alerts_by_key index
            if old_subscription_key in self._alerts_by_key:
                self._alerts_by_key[old_subscription_key].discard(alert_id_key)
                if not self._alerts_by_key[old_subscription_key]:
                    del self._alerts_by_key[old_subscription_key]
                logger.info("[ALERT_UPDATE] Removed old subscription_key index: %s", old_subscription_key)
            else:
                logger.warning("[ALERT_UPDATE] Old subscription_key not in _alerts_by_key: %s", old_subscription_key)

            # Cleanup old K-line cache (optional, as it may be shared)
            if old_subscription_key in self._kline_cache:
                del self._kline_cache[old_subscription_key]
                logger.info("[ALERT_UPDATE] Removed old K-line cache: %s", old_subscription_key)
            else:
                logger.info("[ALERT_UPDATE] Old subscription_key not in _kline_cache: %s", old_subscription_key)

            # Cleanup old subscription in database (remove signal-service from subscribers)
            # Note: Only remove if no other alerts are using this subscription_key
            other_alerts_using_old_key = False
            for key, alert_ids in self._alerts_by_key.items():
                if key == old_subscription_key and len(alert_ids) > 0:
                    other_alerts_using_old_key = True
                    break

            if not other_alerts_using_old_key:
                await self._realtime_repo.remove_subscription(old_subscription_key)

        # ========== Step 4: Create new AlertSignal ==========
        # Create trigger state for the alert
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

        # Store alert signal (AlertSignal contains both config and strategy)
        # If old_alert exists, preserve created_at; otherwise use now
        created_at = old_alert.created_at if old_alert else datetime.utcnow()

        self._alerts[alert_id] = AlertSignal(
            alert_id=alert_id,
            name=alert.name,
            strategy_type=alert.strategy_type,
            symbol=alert.symbol,
            interval=alert.interval,
            trigger_type=alert.trigger_type,
            params=alert.params,
            is_enabled=alert.is_enabled,
            strategy=strategy,
            trigger_state=TriggerState(),
            created_at=created_at,
            updated_at=datetime.utcnow(),
        )

        # ========== Step 5: Update indexes ==========
        # Update alerts index by subscription_key
        if new_subscription_key not in self._alerts_by_key:
            self._alerts_by_key[new_subscription_key] = set()
        self._alerts_by_key[new_subscription_key].add(alert_id)

        # Ensure subscription exists in database (only if is_enabled)
        if new_is_enabled:
            existing = await self._realtime_repo.get_by_subscription_key(new_subscription_key)
            if existing is None:
                await self._realtime_repo.insert_subscription(
                    subscription_key=new_subscription_key,
                    data_type="KLINE",
                )
                logger.info("[ALERT_UPDATE] Created subscription in DB: %s", new_subscription_key)

        logger.info(
            "[ALERT_UPDATE] Alert reloaded successfully: id=%s name=%s subscription_key=%s "
            "(current _alerts_by_key: %s)",
            alert_id,
            alert.name,
            new_subscription_key,
            list(self._alerts_by_key.keys()),
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

    async def _load_alerts_from_db(self) -> None:
        """Load alert configurations from alert_signals table."""
        # Get enabled alerts from database
        db_alerts = await self._alert_repo.find_enabled()

        for alert in db_alerts:
            # Use string as key for consistency
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

            # Create strategy instance based on alert's strategy_type
            strategy = await self._create_strategy(alert)

            # Store alert signal (AlertSignal contains both config and strategy)
            self._alerts[alert_id] = AlertSignal(
                alert_id=alert_id,
                name=alert.name,
                strategy_type=alert.strategy_type,
                symbol=alert.symbol,
                interval=alert.interval,
                trigger_type=alert.trigger_type,
                params=alert.params,
                is_enabled=alert.is_enabled,
                strategy=strategy,
                trigger_state=TriggerState(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Build subscription key and index by subscription_key
            subscription_key = _build_subscription_key(alert.symbol, alert.interval)
            if subscription_key not in self._alerts_by_key:
                self._alerts_by_key[subscription_key] = set()
            self._alerts_by_key[subscription_key].add(alert_id)

        logger.info(
            "[STARTUP] Loaded %d alert configurations, subscription_keys: %s",
            len(db_alerts),
            list(self._alerts_by_key.keys()),
        )

    async def _create_strategy(self, alert: AlertConfigRecord) -> Strategy:
        """Create strategy instance based on alert configuration.

        Args:
            alert: Alert configuration record from alert_signals table.

        Returns:
            Strategy instance.

        Raises:
            ValueError: If strategy type is unknown.
        """
        strategy_type = alert.strategy_type

        if not strategy_type:
            raise ValueError(f"Alert {alert.name} has no strategy_type configured")

        # Direct import mapping - no fallbacks
        # Each strategy type must be explicitly mapped to avoid confusion
        strategy_map = {
            # MACD 做多策略
            "MACDResonanceStrategyV5": (
                "src.strategies.macd_resonance_strategy",
                "MACDResonanceStrategyV5",
            ),
            "MACDResonanceStrategyV6": (
                "src.strategies.macd_resonance_strategy",
                "MACDResonanceStrategyV6",
            ),
            "MACDResonanceStrategyV601": (
                "src.strategies.macd_resonance_strategy",
                "MACDResonanceStrategyV601",
            ),
            # MACD 做空策略
            "MACDResonanceShortStrategy": (
                "src.strategies.macd_resonance_strategy",
                "MACDResonanceShortStrategy",
            ),
            "MACDResonanceShortStrategyV1": (
                "src.strategies.macd_resonance_strategy",
                "MACDResonanceShortStrategyV1",
            ),
            # Alpha 策略
            "Alpha01Strategy": (
                "src.strategies.alpha_01_strategy",
                "Alpha01Strategy",
            ),
            # 随机策略
            "RandomStrategy": (
                "src.strategies.random_strategy",
                "RandomStrategy",
            ),
        }

        if strategy_type not in strategy_map:
            raise ValueError(
                f"Unknown strategy type '{strategy_type}' for alert '{alert.name}'. "
                f"Available strategies: {list(strategy_map.keys())}"
            )

        module_path, class_name = strategy_map[strategy_type]

        # Use importlib for reliable dynamic import
        import importlib

        try:
            module = importlib.import_module(module_path)
            strategy_class = getattr(module, class_name)
            return strategy_class()
        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"Failed to load strategy '{strategy_type}' from module '{module_path}': {e}"
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

                await asyncio.sleep(2)

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
        - Listen for task.completed and task.failed notifications
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
                """Handle task.completed notification."""
                try:
                    data = json.loads(payload)
                    if data.get("id") == task_id:
                        completed_event.set()
                except Exception:
                    pass

            async def handle_failed(
                connection: Any, pid: int, channel: str, payload: str
            ) -> None:
                """Handle task.failed notification."""
                try:
                    data = json.loads(payload)
                    if data.get("id") == task_id:
                        failed_event.set()
                except Exception:
                    pass

            # Register listeners
            await conn.add_listener("task.completed", handle_completed)
            await conn.add_listener("task.failed", handle_failed)

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
        - Listen for task.completed and task.failed notifications
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
            """Handle task.completed notification."""
            try:
                data = json.loads(payload)
                if data.get("id") == task_id:
                    completed_event.set()
            except Exception:
                pass

        async def handle_failed(
            connection: Any, pid: int, channel: str, payload: str
        ) -> None:
            """Handle task.failed notification."""
            try:
                data = json.loads(payload)
                if data.get("id") == task_id:
                    failed_event.set()
            except Exception:
                pass

        # Register listeners on the provided connection
        await conn.add_listener("task.completed", handle_completed)
        await conn.add_listener("task.failed", handle_failed)

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
            await conn.remove_listener("task.completed", handle_completed)
            await conn.remove_listener("task.failed", handle_failed)

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
        """Handle realtime.update notification.

        Args:
            notification: The notification payload from pg_notify.
        """
        if not self._running:
            return

        # Schedule the async handler
        asyncio.create_task(self._process_realtime_update(notification))

    async def _process_realtime_update(self, notification: dict[str, Any]) -> None:
        """Process a realtime.update notification.

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
                self._alerts[alert_id] = AlertSignal(
                    alert_id=loaded_alert.alert_id,
                    name=loaded_alert.name,
                    strategy_type=loaded_alert.strategy_type,
                    symbol=loaded_alert.symbol,
                    interval=loaded_alert.interval,
                    trigger_type=loaded_alert.trigger_type,
                    params=loaded_alert.params,
                    is_enabled=loaded_alert.is_enabled,
                    strategy=loaded_alert.strategy,
                    trigger_state=new_trigger_state,
                    created_at=loaded_alert.created_at,
                    updated_at=datetime.utcnow(),
                )
                return
        except ValueError as e:
            logger.warning("Invalid trigger type: %s", e)
            return

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

        # Get strategy from AlertSignal
        strategy = loaded_alert.strategy

        # Create AlertSignal instance to use calculate method
        alert_signal = AlertSignal(
            alert_id=str(alert_id),
            name=loaded_alert.name,
            strategy_type=loaded_alert.strategy_type,
            symbol=loaded_alert.symbol,
            interval=loaded_alert.interval,
            trigger_type=loaded_alert.trigger_type,
            params=loaded_alert.params,
            is_enabled=loaded_alert.is_enabled,
            strategy=strategy,
            trigger_state=loaded_alert.trigger_state,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # DEBUG: Log the kline data input to strategy
        # Extract time range from the actual kline data passed to strategy
        if len(cached_klines) > 0:
            # First kline time
            first_k_time_raw = cached_klines.iloc[0]["time"]
            first_k_time = _format_kline_time(first_k_time_raw)

            # Last kline time (could be from kline_data if not closed)
            if kline_data and not is_closed:
                # Use kline_data as the last one
                current_k_time_raw = kline_data.get("k", {}).get("t")
                last_k_time = _format_kline_time(current_k_time_raw)
                input_time_range = f"[{first_k_time} -> {last_k_time}] (with current)"
            else:
                last_k_time_raw = cached_klines.iloc[-1]["time"]
                last_k_time = _format_kline_time(last_k_time_raw)
                input_time_range = f"[{first_k_time} -> {last_k_time}]"

            logger.debug(
                "[INPUT_KLINE] alert=%s klines=%d trigger_type=%s is_closed=%s time_range=%s",
                loaded_alert.name,
                len(cached_klines),
                trigger_type,
                is_closed,
                input_time_range,
            )

        # Calculate signal with ohlcv DataFrame
        output = alert_signal.calculate(ohlcv)

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
        self._alerts[alert_id] = AlertSignal(
            alert_id=loaded_alert.alert_id,
            name=loaded_alert.name,
            strategy_type=loaded_alert.strategy_type,
            symbol=loaded_alert.symbol,
            interval=loaded_alert.interval,
            trigger_type=loaded_alert.trigger_type,
            params=loaded_alert.params,
            is_enabled=loaded_alert.is_enabled,
            strategy=loaded_alert.strategy,
            trigger_state=new_trigger_state,
            created_at=loaded_alert.created_at,
            updated_at=datetime.utcnow(),
        )
