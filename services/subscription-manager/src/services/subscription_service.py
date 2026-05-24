"""SubscriptionService - listens for subscription_task_new and processes tasks."""

import json
import logging

import asyncpg

from src.db.heartbeat_repository import HeartbeatRepository
from src.db.realtime_data_repository import RealtimeDataRepository
from src.db.subscription_tasks_repo import SubscriptionTasksRepository
from src.models.subscription_models import SubscriptionTaskData

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Listens on subscription_task_new channel and processes subscription tasks.

    Routes subscribe/unsubscribe tasks to RealtimeDataRepository,
    which is the sole write authority for the realtime_data table.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._realtime_repo = RealtimeDataRepository(pool)
        self._tasks_repo = SubscriptionTasksRepository(pool)
        self._heartbeat_repo = HeartbeatRepository(pool)
        self._conn: asyncpg.Connection | None = None
        self._running = False

    async def start(self) -> None:
        """Acquire a dedicated connection, start listening, then recover.

        LISTEN is registered BEFORE recovery to avoid a race condition:
        any task inserted between the recovery SELECT and add_listener()
        would otherwise have its NOTIFY permanently lost.
        """
        self._running = True

        # Acquire connection and start listening first
        self._conn = await self._pool.acquire()
        await self._conn.add_listener("subscription_task_new", self._on_task)

        # Recover pending tasks; new tasks arriving during recovery
        # are processed by _on_task in parallel (both paths are idempotent)
        await self._recover_pending_tasks()

        # Reconcile realtime_data state: remove dead subscribers
        await self._reconcile_state()

        logger.info("SubscriptionService started, listening on subscription_task_new")

    async def _recover_pending_tasks(self) -> None:
        """Compact and process pending tasks from before a restart.

        For each (subscription_key, subscriber) group, only the last task
        (by id) is processed; earlier tasks in the same group are marked
        completed since their effect is superseded.
        """
        async with self._pool.acquire() as conn:
            # Mark superseded tasks as completed
            result = await conn.execute(
                """
                UPDATE subscription_tasks
                SET status = 'completed', updated_at = NOW()
                WHERE status = 'pending'
                  AND id NOT IN (
                      SELECT MAX(id) FROM subscription_tasks
                      WHERE status = 'pending'
                      GROUP BY subscription_key, subscriber
                  )
                """
            )
            compacted = int(result.split()[-1]) if result and "UPDATE" in result else 0

            # Fetch remaining (last per group) tasks
            rows = await conn.fetch(
                "SELECT id, type, subscription_key, data_type, subscriber "
                "FROM subscription_tasks WHERE status = 'pending' "
                "ORDER BY id"
            )

        if compacted > 0:
            logger.info("Compacted %d superseded pending tasks", compacted)
        if not rows:
            return

        logger.info("Recovering %d pending tasks from before restart", len(rows))
        for row in rows:
            task = SubscriptionTaskData(**dict(row))
            await self._process_task(task)

    async def _reconcile_state(self) -> None:
        """Clean up dead subscribers from realtime_data on startup.

        Queries service_heartbeats for subscribers whose heartbeat is older
        than 30 seconds, then removes them from all realtime_data rows.
        Empty rows are automatically deleted by remove_subscriber_from_all.
        """
        try:
            offline = await self._heartbeat_repo.get_offline_subscribers(30)
        except Exception:
            logger.exception("Failed to query offline subscribers for reconciliation")
            return

        for subscriber in offline:
            try:
                deleted = await self._realtime_repo.remove_subscriber_from_all(subscriber)
                if deleted > 0:
                    logger.info(
                        "Startup reconcile: removed dead subscriber %s from %d rows",
                        subscriber, deleted,
                    )
            except Exception:
                logger.exception("Failed to remove dead subscriber: %s", subscriber)

    async def stop(self) -> None:
        """Stop listening and release the connection."""
        self._running = False
        if self._conn is not None:
            try:
                await self._conn.remove_listener("subscription_task_new", self._on_task)
                await self._pool.release(self._conn)
            except Exception:
                pass
            self._conn = None
        logger.info("SubscriptionService stopped")

    async def _on_task(self, conn: asyncpg.Connection, pid: int, channel: str, payload: str) -> None:
        """Handle incoming subscription_task_new notification."""
        if not self._running:
            return
        try:
            notification = json.loads(payload)
            data = notification.get("data", {})
            task = SubscriptionTaskData(**data)
            logger.debug("Received task: type=%s id=%s", task.type, task.id)
            await self._process_task(task)
        except Exception:
            logger.exception("Failed to process subscription task: %s", payload)

    async def _process_task(self, task: SubscriptionTaskData) -> None:
        """Route task by type to the appropriate handler."""
        try:
            if task.type == "subscribe":
                await self._handle_subscribe(task)
            elif task.type == "unsubscribe":
                await self._handle_unsubscribe(task)
            else:
                logger.warning("Unknown task type: %s", task.type)
                await self._tasks_repo.mark_failed(task.id, f"Unknown type: {task.type}")
                return

            await self._tasks_repo.mark_completed(task.id)
        except Exception as e:
            logger.exception("Task %d failed: %s", task.id, e)
            await self._tasks_repo.mark_failed(task.id, str(e))

    async def _handle_subscribe(self, task: SubscriptionTaskData) -> None:
        """Handle a subscribe task."""
        if not task.subscription_key or not task.data_type:
            raise ValueError("subscribe task requires subscription_key and data_type")
        await self._realtime_repo.add_subscription(
            task.subscription_key, task.data_type, task.subscriber
        )

    async def _handle_unsubscribe(self, task: SubscriptionTaskData) -> None:
        """Handle an unsubscribe task."""
        if not task.subscription_key:
            raise ValueError("unsubscribe task requires subscription_key")
        await self._realtime_repo.remove_subscription(
            task.subscription_key, task.subscriber
        )
