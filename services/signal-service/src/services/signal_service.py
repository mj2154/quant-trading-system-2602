"""Core signal service logic."""

import asyncio
import dataclasses
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import pandas as pd

from ..db.alert_config_repository import AlertConfigRepository
from ..db.database import Database
from ..db.realtime_data_repository import RealtimeDataRepository
from ..db.strategy_signals_repository import StrategySignalsRepository
from ..db.tasks_repository import TasksRepository
from ..listener.alert_signal_listener import AlertSignalListener
from ..listener.realtime_update_listener import RealtimeUpdateListener
from .alert_manager import AlertLifecycleManager
from .alert_signal import LoadedAlertConfig
from .constants import REQUIRED_KLINES, TV_INTERVAL_TO_MS
from .kline_cache import _update_kline_cache
from .kline_manager import KlineCacheManager
from .kline_utils import (
    _build_ohlcv_for_trigger_type,
    _format_kline_time,
    _get_interval_ms,
)
from .kline_validator import (
    _check_kline_continuity_in_dataframe,
    _validate_cache_for_kline_close,
)
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

        self._alert_mgr = AlertLifecycleManager(
            db, self._alert_repo, self._realtime_repo,
            self._alerts, self._alerts_by_key,
        )
        self._kline_mgr = KlineCacheManager(
            db, self._realtime_repo, self._tasks_repo, self._kline_cache,
        )

        self._listener: RealtimeUpdateListener | None = None
        self._alert_listener: AlertSignalListener | None = None
        self._connection = None
        self._running = False

    async def start(self) -> None:
        """Start the signal service."""
        logger.info("Starting signal service")
        self._running = True

        await self._alert_mgr.cleanup_stale_subscriptions()
        await self._alert_mgr.load_alerts_from_db()
        await self._alert_mgr.ensure_subscriptions(
            self._kline_mgr.init_cache_for_key
        )

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
        asyncio.create_task(self._alert_mgr.reload_single_alert(data))

    def _handle_alert_update(self, data: dict[str, Any]) -> None:
        """Handle updated alert signal notification."""
        if not self._running:
            return

        alert_id = data.get("id")
        name = data.get("name")
        logger.info("Alert signal update detected: id=%s name=%s, reloading...", alert_id, name)

        # Reload alert configurations from database
        asyncio.create_task(self._alert_mgr.reload_single_alert(data))

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
        asyncio.create_task(self._alert_mgr.handle_alert_delete_async(data))

    async def reload_configs(self) -> None:
        await self._alert_mgr.reload_configs()

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
                    await self._kline_mgr.init_cache_for_key(subscription_key)

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
                    await self._kline_mgr.fill_kline_data(subscription_key, symbol, interval)
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
        """Process signal calculation for a single alert."""
        loaded_alert = self._alerts.get(alert_id)
        if not loaded_alert or not loaded_alert.is_enabled:
            return

        trigger_type = loaded_alert.trigger_type

        # Debug: log kline time range and trigger info
        first_kline_time_raw = cached_klines.iloc[0]["time"] if len(cached_klines) > 0 else None
        last_kline_time_raw = cached_klines.iloc[-1]["time"] if len(cached_klines) > 0 else None
        current_kline_time_raw = kline_data.get("k", {}).get("t") if kline_data else None

        logger.debug(
            "[DEBUG_SIGNAL] alert=%s trigger_type=%s is_closed=%s "
            "kline_range=[%s -> %s] current_kline_time=%s",
            loaded_alert.name, trigger_type, is_closed,
            _format_kline_time(first_kline_time_raw),
            _format_kline_time(last_kline_time_raw),
            _format_kline_time(current_kline_time_raw),
        )

        if not self._resolve_should_calculate(trigger_type, is_closed):
            return

        should_proceed, new_trigger_state = self._check_trigger_and_update_state(
            alert_id, loaded_alert, kline_data, event_time,
        )
        if not should_proceed:
            return

        repaired_cache = await self._validate_and_repair_cache(
            loaded_alert, subscription_key, cached_klines, kline_data, trigger_type,
        )
        if repaired_cache is None:
            return

        await self._calculate_and_save_signal(
            alert_id, loaded_alert, subscription_key, trigger_type,
            repaired_cache, new_trigger_state,
        )

    @staticmethod
    def _resolve_should_calculate(trigger_type: str, is_closed: bool) -> bool:
        """Determine if we should calculate based on trigger type."""
        if trigger_type == "each_kline":
            return True
        if trigger_type == "each_kline_close":
            return is_closed
        if trigger_type == "each_minute":
            return True
        return is_closed

    def _check_trigger_and_update_state(
        self,
        alert_id: UUID,
        loaded_alert: LoadedAlertConfig,
        kline_data: dict[str, Any],
        event_time: datetime,
    ) -> tuple[bool, TriggerState | None]:
        """Check trigger engine and update state if not executing.

        Returns (True, new_trigger_state) if should proceed with calculation,
        or (False, None) if should skip this update.
        """
        try:
            trigger_type_enum = TriggerType(loaded_alert.trigger_type)
            trigger_engine = get_trigger_engine(trigger_type_enum)
            should_execute, new_trigger_state = trigger_engine.should_execute(
                loaded_alert.trigger_state,
                kline_data or {},
                event_time,
            )

            if not should_execute:
                self._alerts[alert_id] = dataclasses.replace(
                    loaded_alert,
                    trigger_state=new_trigger_state,
                    updated_at=datetime.utcnow(),
                )
                return False, None

            return True, new_trigger_state
        except ValueError as e:
            logger.warning("Invalid trigger type: %s", e)
            return False, None

    async def _validate_and_repair_cache(
        self,
        loaded_alert: LoadedAlertConfig,
        subscription_key: str,
        cached_klines: pd.DataFrame,
        kline_data: dict[str, Any],
        trigger_type: str,
    ) -> pd.DataFrame | None:
        """Validate cache correctness and continuity, repair if needed.

        Returns repaired DataFrame or None if fatally broken.
        """
        # Cache validation for each_kline_close trigger
        if trigger_type == "each_kline_close":
            cache_valid, _ = _validate_cache_for_kline_close(
                cached_klines, kline_data,
            )
            if not cache_valid:
                repaired = await self._repair_and_revalidate(
                    loaded_alert, subscription_key, cached_klines, kline_data,
                    validator=_validate_cache_for_kline_close,
                    check_name="CACHE_VALIDATION",
                )
                if repaired is None:
                    return None
                cached_klines = repaired

        # Kline count and continuity check
        interval_ms = _get_interval_ms(loaded_alert.interval)

        if len(cached_klines) < REQUIRED_KLINES:
            last_time = cached_klines.iloc[-1]["time"] if not cached_klines.empty else "N/A"
            last_close = cached_klines.iloc[-1]["close"] if not cached_klines.empty else "N/A"
            logger.error(
                "[INSUFFICIENT_KLINES] alert=%s got=%d need=%d "
                "cached_last_time=%s cached_last_close=%s",
                loaded_alert.name, len(cached_klines), REQUIRED_KLINES,
                last_time, last_close,
            )
            return None

        continuity_valid, _ = _check_kline_continuity_in_dataframe(
            cached_klines, interval_ms,
        )
        if not continuity_valid:
            repaired = await self._repair_and_revalidate(
                loaded_alert, subscription_key, cached_klines, kline_data,
                validator=lambda df, _kd: _check_kline_continuity_in_dataframe(df, interval_ms),
                check_name="KLINE_CONTINUITY",
            )
            if repaired is None:
                return None
            cached_klines = repaired

        return cached_klines

    async def _repair_and_revalidate(
        self,
        loaded_alert: LoadedAlertConfig,
        subscription_key: str,
        cached_klines: pd.DataFrame,
        kline_data: dict[str, Any],
        validator: Any,
        check_name: str,
    ) -> pd.DataFrame | None:
        """Attempt cache repair and re-validate. Returns repaired DF or None."""
        logger.warning(
            "[%s_FAILED] alert=%s, attempting repair", check_name, loaded_alert.name,
        )

        await self._kline_mgr.init_cache_for_key(subscription_key)
        repaired = self._kline_cache.get(subscription_key, pd.DataFrame())

        valid, reason = validator(repaired, kline_data)
        if not valid:
            last_time = repaired.iloc[-1]["time"] if not repaired.empty else "N/A"
            last_close = repaired.iloc[-1]["close"] if not repaired.empty else "N/A"
            received_time = kline_data.get("k", {}).get("t")
            logger.error(
                "[%s_FATAL] alert=%s repair_failed reason=%s "
                "cached_last_time=%s cached_last_close=%s received_time=%s",
                check_name, loaded_alert.name, reason,
                last_time, last_close, received_time,
            )
            return None

        logger.info(
            "[CACHE_REPAIRED] alert=%s subscription_key=%s (%s)",
            loaded_alert.name, subscription_key, check_name,
        )
        return repaired

    async def _calculate_and_save_signal(
        self,
        alert_id: UUID,
        loaded_alert: LoadedAlertConfig,
        subscription_key: str,
        trigger_type: str,
        cached_klines: pd.DataFrame,
        new_trigger_state: TriggerState,
    ) -> None:
        """Build ohlcv, calculate signal, and save to database."""
        ohlcv = _build_ohlcv_for_trigger_type(cached_klines)

        if len(ohlcv) > 0:
            first_time = ohlcv.index[0] if hasattr(ohlcv.index[0], 'isoformat') else str(ohlcv.index[0])
            last_time = ohlcv.index[-1] if hasattr(ohlcv.index[-1], 'isoformat') else str(ohlcv.index[-1])
            logger.debug(
                "[DEBUG_OHLCV] alert=%s ohlcv_len=%d range=[%s -> %s]",
                loaded_alert.name, len(ohlcv), first_time, last_time,
            )

        if len(ohlcv) < REQUIRED_KLINES:
            logger.warning(
                "Insufficient klines for signal calculation: alert=%s got=%d need=%d",
                loaded_alert.name, len(ohlcv), REQUIRED_KLINES,
            )
            return

        last_kline = ohlcv.iloc[-1]
        logger.info(
            "[CALC_START] alert=%s strategy=%s trigger_type=%s "
            "last_kline_open_time=%s last_kline_close_price=%s "
            "ohlcv_count=%d symbol=%s interval=%s",
            loaded_alert.name, loaded_alert.strategy_type, trigger_type,
            _format_kline_time(last_kline["time"]), last_kline["close"],
            len(ohlcv), loaded_alert.symbol, loaded_alert.interval,
        )

        output = loaded_alert.calculate(ohlcv)

        if output.signal_value is None:
            logger.debug(
                "[DEBUG_SKIP] alert=%s signal_reason=%s (no signal generated)",
                loaded_alert.name, output.signal_reason,
            )
            return

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
            metadata={"processed_at": datetime.utcnow().isoformat()},
            created_by=loaded_alert.created_by,
        )

        logger.info(
            "Signal computed and saved: alert=%s symbol=%s interval=%s signal_value=%s reason=%s",
            loaded_alert.name, loaded_alert.symbol, loaded_alert.interval,
            output.signal_value, output.signal_reason,
        )

        self._alerts[alert_id] = dataclasses.replace(
            loaded_alert,
            trigger_state=new_trigger_state,
            updated_at=datetime.utcnow(),
        )
