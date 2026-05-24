"""Alert lifecycle management.

Handles loading, reloading, creating, and cleaning up alert configurations.
"""
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from ..db.alert_config_repository import AlertConfigRecord, AlertConfigRepository
from ..db.database import Database
from ..db.realtime_data_repository import RealtimeDataRepository
from ..strategies.base import Strategy
from .alert_signal import LoadedAlertConfig
from .subscription_utils import _build_subscription_key
from .trigger_engine import TriggerState, TriggerType, get_trigger_engine

logger = logging.getLogger(__name__)


class AlertLifecycleManager:
    """Manages alert configuration lifecycle: load, reload, delete, subscriptions."""

    def __init__(
        self,
        db: Database,
        alert_repo: AlertConfigRepository,
        realtime_repo: RealtimeDataRepository,
        alerts: dict[UUID, LoadedAlertConfig],
        alerts_by_key: dict[str, set[UUID]],
    ) -> None:
        self._db = db
        self._alert_repo = alert_repo
        self._realtime_repo = realtime_repo
        self._alerts = alerts
        self._alerts_by_key = alerts_by_key

    @staticmethod
    def remove_alert_from_memory(
        alerts: dict[UUID, LoadedAlertConfig],
        alerts_by_key: dict[str, set[UUID]],
        alert_id_str: str,
    ) -> str | None:
        """Remove alert from memory indexes. Returns old subscription key or None."""
        if alert_id_str not in alerts:
            return None
        old_alert = alerts[alert_id_str]
        old_subscription_key = _build_subscription_key(old_alert.symbol, old_alert.interval)
        del alerts[alert_id_str]
        if old_subscription_key in alerts_by_key:
            alerts_by_key[old_subscription_key].discard(alert_id_str)
            if not alerts_by_key[old_subscription_key]:
                del alerts_by_key[old_subscription_key]
        return old_subscription_key

    async def handle_alert_delete_async(self, data: dict[str, Any]) -> None:
        """Async cleanup logic for deleted alert."""
        alert_id = data.get("id")
        if not alert_id:
            return

        try:
            alert_id_str = str(alert_id)
        except ValueError:
            logger.warning("Invalid alert ID format: %s", alert_id)
            return

        old_subscription_key = self.remove_alert_from_memory(
            self._alerts, self._alerts_by_key, alert_id_str
        )
        if old_subscription_key is None:
            return

        await self.cleanup_subscription_if_unused(old_subscription_key)
        logger.info(
            "[ALERT_DELETE] Alert deleted: id=%s subscription_key=%s",
            alert_id, old_subscription_key,
        )

    async def reload_single_alert(self, data: dict[str, Any]) -> None:
        """Reload a single alert from database notification.

        Simplified logic: Database is single source of truth.
        - Update memory state from DB
        - If enabled: ensure subscription exists
        - If disabled: ensure subscription removed
        """
        alert_id_str = data.get("id")
        if not alert_id_str:
            return

        try:
            UUID(alert_id_str)
        except ValueError:
            logger.warning("Invalid alert ID format: %s", alert_id_str)
            return

        alert = await self._alert_repo.find_by_id(alert_id_str)
        if not alert:
            logger.info(
                "[ALERT_UPDATE] Alert deleted from DB: %s, cleaning up", alert_id_str
            )
            old_sub_key = self.remove_alert_from_memory(
                self._alerts, self._alerts_by_key, alert_id_str
            )
            if old_sub_key:
                await self.cleanup_subscription_if_unused(old_sub_key)
            return

        alert_id = str(alert.id)
        subscription_key = _build_subscription_key(alert.symbol, alert.interval)

        try:
            trigger_type_enum = TriggerType(alert.trigger_type)
            get_trigger_engine(trigger_type_enum)
        except ValueError:
            logger.warning(
                "Unknown trigger type %s for alert %s, using EACH_KLINE_CLOSE",
                alert.trigger_type, alert.name,
            )
            get_trigger_engine(TriggerType.EACH_KLINE_CLOSE)

        strategy = await self._create_strategy(alert)

        old_alert = self._alerts.get(alert_id)
        created_at = old_alert.created_at if old_alert else datetime.utcnow()

        old_subscription_key = None
        if old_alert and old_alert.is_enabled:
            old_subscription_key = _build_subscription_key(old_alert.symbol, old_alert.interval)

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

        if alert.is_enabled:
            if old_subscription_key and old_subscription_key != subscription_key:
                if old_subscription_key in self._alerts_by_key:
                    self._alerts_by_key[old_subscription_key].discard(alert_id)
                    if not self._alerts_by_key[old_subscription_key]:
                        del self._alerts_by_key[old_subscription_key]
                    logger.info(
                        "[ALERT_UPDATE] Removed alert from old subscription: alert_id=%s old_key=%s",
                        alert_id, old_subscription_key,
                    )
            if subscription_key not in self._alerts_by_key:
                self._alerts_by_key[subscription_key] = set()
            self._alerts_by_key[subscription_key].add(alert_id)
        else:
            if subscription_key in self._alerts_by_key:
                self._alerts_by_key[subscription_key].discard(alert_id)
                if not self._alerts_by_key[subscription_key]:
                    del self._alerts_by_key[subscription_key]

        if alert.is_enabled:
            if old_subscription_key and old_subscription_key != subscription_key:
                await self.cleanup_subscription_if_unused(old_subscription_key)
            existing = await self._realtime_repo.get_by_subscription_key(subscription_key)
            if existing is None:
                await self._realtime_repo.insert_subscription(
                    subscription_key=subscription_key, data_type="KLINE",
                )
                logger.info("[ALERT_UPDATE] Created subscription: %s", subscription_key)
        else:
            await self.cleanup_subscription_if_unused(subscription_key)

        logger.info(
            "[ALERT_UPDATE] alert_id=%s name=%s enabled=%s subscription_key=%s",
            alert_id, alert.name, alert.is_enabled, subscription_key,
        )

    async def reload_configs(self) -> None:
        """Reload alert configurations from database."""
        logger.info("Reloading alert configurations")
        old_alert_ids = set(self._alerts.keys())
        await self.load_alerts_from_db()
        new_alert_ids = set(self._alerts.keys())

        added = new_alert_ids - old_alert_ids
        removed = old_alert_ids - new_alert_ids
        if added:
            logger.info("Added %d new alerts", len(added))
        if removed:
            logger.info("Removed %d alerts", len(removed))

    async def cleanup_stale_subscriptions(self) -> None:
        """Clean up stale subscriptions on startup.

        Removes all signal-service subscriptions from realtime_data table,
        ensuring subscriptions are always consistent with enabled alert configs.
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
                logger.info("Cleaned up stale subscription: %s", subscription_key)
            else:
                logger.warning("Failed to clean up subscription: %s", subscription_key)

        logger.info(
            "[CLEANUP] Cleaned up %d stale subscriptions: %s",
            len(cleaned_keys), cleaned_keys,
        )

    async def load_alerts_from_db(self) -> None:
        """Load all alert configurations from database.

        All alerts are loaded into _alerts (regardless of is_enabled).
        Only enabled alerts are added to _alerts_by_key for subscriptions.
        """
        db_alerts = await self._alert_repo.find_all()
        self._alerts.clear()
        self._alerts_by_key.clear()

        for alert in db_alerts:
            alert_id = str(alert.id)

            try:
                trigger_type_enum = TriggerType(alert.trigger_type)
                get_trigger_engine(trigger_type_enum)
            except ValueError:
                logger.warning(
                    "Unknown trigger type %s for alert %s, using EACH_KLINE_CLOSE",
                    alert.trigger_type, alert.name,
                )
                get_trigger_engine(TriggerType.EACH_KLINE_CLOSE)

            strategy = await self._create_strategy(alert)

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
        """Create strategy instance based on alert configuration."""
        from ..strategies.registry import StrategyRegistry

        strategy_type = alert.strategy_type
        if not strategy_type:
            raise ValueError(f"Alert {alert.name} has no strategy_type configured")

        return StrategyRegistry.create_instance(strategy_type)

    async def cleanup_subscription_if_unused(self, subscription_key: str) -> None:
        """Remove subscription from DB if no enabled alerts use it."""
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

    async def ensure_subscriptions(self, kline_init_callback) -> None:
        """Ensure subscriptions exist for all configured alerts.

        Args:
            kline_init_callback: Async callable(subscription_key) that initializes
                kline cache for a given subscription key.
        """
        logger.info("Ensuring subscriptions for configured alerts")
        processed_keys: set[str] = set()

        for loaded_alert in self._alerts.values():
            if not loaded_alert.is_enabled:
                continue

            subscription_key = _build_subscription_key(
                loaded_alert.symbol, loaded_alert.interval,
            )

            existing = await self._realtime_repo.get_by_subscription_key(subscription_key)
            if existing is None:
                await self._realtime_repo.insert_subscription(
                    subscription_key=subscription_key, data_type="KLINE",
                )
                logger.info(
                    "Created subscription: subscription_key=%s alert=%s",
                    subscription_key, loaded_alert.name,
                )

            if subscription_key not in processed_keys:
                await kline_init_callback(subscription_key)
                processed_keys.add(subscription_key)
