"""Repository for service_heartbeats table."""

import logging

import asyncpg

logger = logging.getLogger(__name__)


class HeartbeatRepository:
    """Repository for querying service_heartbeats table."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_offline_subscribers(self, threshold_seconds: int = 30) -> list[str]:
        """Get subscribers whose last heartbeat is older than threshold."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT subscriber_id FROM service_heartbeats
                WHERE last_heartbeat < NOW() - INTERVAL '1 second' * $1
                """,
                threshold_seconds,
            )
        return [row["subscriber_id"] for row in rows]

    async def is_service_alive(
        self, service_id: str, threshold_seconds: int = 30
    ) -> bool:
        """Check if a service has a recent heartbeat in service_heartbeats."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM service_heartbeats
                WHERE subscriber_id = $1
                  AND last_heartbeat > NOW() - INTERVAL '1 second' * $2
                """,
                service_id,
                threshold_seconds,
            )
        return row is not None
