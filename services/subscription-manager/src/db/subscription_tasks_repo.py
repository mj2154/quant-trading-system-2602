"""Repository for subscription_tasks table - marking tasks as completed/failed."""

import logging

import asyncpg

logger = logging.getLogger(__name__)


class SubscriptionTasksRepository:
    """Repository for updating subscription_tasks status."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def mark_completed(self, task_id: int) -> None:
        """Mark a task as completed."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE subscription_tasks SET status='completed', updated_at=NOW() WHERE id=$1",
                task_id,
            )
        logger.debug("Task %d marked completed", task_id)

    async def mark_failed(self, task_id: int, error: str = "") -> None:
        """Mark a task as failed."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE subscription_tasks SET status='failed', "
                "payload = payload || jsonb_build_object('error', $2::text), "
                "updated_at = NOW() WHERE id = $1",
                task_id, error,
            )
        logger.warning("Task %d marked failed: %s", task_id, error)
