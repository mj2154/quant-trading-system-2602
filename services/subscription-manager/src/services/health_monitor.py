"""HealthMonitor - monitors data freshness and subscriber liveness."""

import asyncio
import logging

import asyncpg

from src.db.heartbeat_repository import HeartbeatRepository
from src.db.realtime_data_repository import RealtimeDataRepository

logger = logging.getLogger(__name__)

STALE_THRESHOLD_SECONDS = 30
LIVENESS_THRESHOLD_SECONDS = 30
CHECK_INTERVAL_SECONDS = 10


class HealthMonitor:
    """Periodically checks data freshness and subscriber liveness.

    - Data freshness: if a non-USERDATA realtime_data row has not been
      updated within STALE_THRESHOLD_SECONDS, trigger delete_and_recreate
      to force re-subscription.
    - Subscriber liveness: if a subscriber's heartbeat is older than
      LIVENESS_THRESHOLD_SECONDS, remove all their subscriptions.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._realtime_repo = RealtimeDataRepository(pool)
        self._heartbeat_repo = HeartbeatRepository(pool)
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background monitoring loop."""
        self._task = asyncio.create_task(self._run_loop())
        logger.info("HealthMonitor started (interval=%ds, stale=%ds, liveness=%ds)",
                     CHECK_INTERVAL_SECONDS, STALE_THRESHOLD_SECONDS, LIVENESS_THRESHOLD_SECONDS)

    async def stop(self) -> None:
        """Stop the monitoring loop."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("HealthMonitor stopped")

    async def _run_loop(self) -> None:
        """Main monitoring loop."""
        while True:
            try:
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                await self._check_data_freshness()
                await self._check_subscriber_liveness()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("HealthMonitor check cycle failed")

    async def _check_data_freshness(self) -> None:
        """Check all non-USERDATA rows for data staleness.

        Only triggers recovery if binance-service is alive (has recent heartbeat).
        If binance-service is down or reconnecting, skip recovery to avoid
        useless delete+recreate cycles.
        """
        # 先检查币安服务是否存活，如果挂了则跳过恢复
        if not await self._heartbeat_repo.is_service_alive("binance-service"):
            logger.debug("binance-service heartbeat missing, skip freshness recovery")
            return

        try:
            rows = await self._realtime_repo.get_all_non_userdata()
        except Exception:
            logger.exception("Failed to fetch realtime_data for freshness check")
            return

        now = None  # computed lazily
        for row in rows:
            updated_at = row.get("updated_at")
            if updated_at is None:
                continue

            now = now or __import__("datetime").datetime.now(tz=updated_at.tzinfo)
            age = (now - updated_at).total_seconds()
            if age > STALE_THRESHOLD_SECONDS:
                key = row["subscription_key"]
                logger.warning(
                    "Data stale: key=%s data_type=%s age=%.0fs, triggering recovery",
                    key, row["data_type"], age,
                )
                try:
                    await self._realtime_repo.delete_and_recreate(key)
                except Exception:
                    logger.exception("Failed to recover stale subscription: %s", key)

    async def _check_subscriber_liveness(self) -> None:
        """Check for offline subscribers and clean up their subscriptions."""
        try:
            offline = await self._heartbeat_repo.get_offline_subscribers(
                LIVENESS_THRESHOLD_SECONDS
            )
        except Exception:
            logger.exception("Failed to check subscriber liveness")
            return

        for subscriber in offline:
            try:
                deleted = await self._realtime_repo.remove_subscriber_from_all(subscriber)
                if deleted > 0:
                    logger.warning(
                        "Subscriber offline: %s, removed %d subscription rows",
                        subscriber, deleted,
                    )
            except Exception:
                logger.exception("Failed to remove subscriptions for: %s", subscriber)
