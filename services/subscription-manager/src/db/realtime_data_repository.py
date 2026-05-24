"""RealtimeData table repository - sole write authority for subscription-manager."""

import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


class RealtimeDataRepository:
    """Repository for realtime_data table.

    This is the SINGLE service authorized to INSERT/DELETE rows and manage
    the subscribers array. All other services go through subscription_tasks.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def add_subscription(
        self, subscription_key: str, data_type: str, subscriber: str
    ) -> str:
        """Add a subscriber to a subscription key. Inserts row if new.

        Returns: 'inserted' if new row, 'updated' if existing row appended.
        """
        query = """
            INSERT INTO realtime_data (subscription_key, data_type, data, subscribers)
            VALUES ($1, $2, '{}'::jsonb, ARRAY[$3])
            ON CONFLICT (subscription_key)
            DO UPDATE SET
                subscribers = ARRAY_APPEND(
                    ARRAY_REMOVE(realtime_data.subscribers, $3),
                    $3
                ),
                updated_at = NOW()
            RETURNING (xmax = 0) as is_insert;
        """
        async with self._pool.acquire() as conn:
            is_insert = await conn.fetchval(query, subscription_key, data_type, subscriber)
        result = "inserted" if is_insert else "updated"
        logger.info("add_subscription: key=%s subscriber=%s result=%s",
                    subscription_key, subscriber, result)
        return result

    async def remove_subscription(
        self, subscription_key: str, subscriber: str
    ) -> str:
        """Remove a subscriber from a subscription key. Deletes row if empty.

        Returns: 'deleted', 'updated', or 'not_found'.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE realtime_data
                SET subscribers = ARRAY_REMOVE(subscribers, $2),
                    updated_at = NOW()
                WHERE subscription_key = $1
                """,
                subscription_key,
                subscriber,
            )
            if "UPDATE 0" in result:
                return "not_found"

            row = await conn.fetchrow(
                "SELECT subscribers FROM realtime_data WHERE subscription_key = $1",
                subscription_key,
            )
            if row is None:
                return "deleted"

            subs = row["subscribers"]
            if subs is None or len(subs) == 0:
                await conn.execute(
                    "DELETE FROM realtime_data WHERE subscription_key = $1",
                    subscription_key,
                )
                logger.info("remove_subscription: key=%s deleted (empty)", subscription_key)
                return "deleted"

            logger.info("remove_subscription: key=%s updated (remaining=%s)",
                        subscription_key, subs)
            return "updated"

    async def delete_and_recreate(self, subscription_key: str) -> bool:
        """Delete a row and re-insert with same subscribers.

        Used for health recovery: force re-subscription via delete+insert
        to trigger subscription_remove + subscription_add notifications.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data_type, subscribers FROM realtime_data WHERE subscription_key = $1",
                subscription_key,
            )
            if row is None:
                logger.warning("delete_and_recreate: key=%s not found", subscription_key)
                return False

            data_type = row["data_type"]
            subscribers = row["subscribers"] or []

            await conn.execute(
                "DELETE FROM realtime_data WHERE subscription_key = $1",
                subscription_key,
            )
            await conn.execute(
                "INSERT INTO realtime_data (subscription_key, data_type, data, subscribers) "
                "VALUES ($1, $2, '{}'::jsonb, $3)",
                subscription_key, data_type, subscribers,
            )
            logger.info("delete_and_recreate: key=%s data_type=%s",
                        subscription_key, data_type)
            return True

    async def get_all_non_userdata(self) -> list[dict[str, Any]]:
        """Get all realtime_data rows except USERDATA type."""
        query = """
            SELECT id, subscription_key, data_type, subscribers, updated_at
            FROM realtime_data
            WHERE data_type != 'USERDATA'
            ORDER BY subscription_key
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
        return [dict(row) for row in rows]

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all realtime_data rows."""
        query = """
            SELECT id, subscription_key, data_type, subscribers, updated_at
            FROM realtime_data
            ORDER BY subscription_key
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
        return [dict(row) for row in rows]

    async def remove_subscriber_from_all(self, subscriber: str) -> int:
        """Remove a subscriber from all rows. Delete empty rows.

        Returns: number of rows fully deleted.
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE realtime_data
                SET subscribers = ARRAY_REMOVE(subscribers, $1),
                    updated_at = NOW()
                WHERE $1 = ANY(subscribers)
                """,
                subscriber,
            )
            result = await conn.execute(
                """
                DELETE FROM realtime_data
                WHERE subscribers IS NULL OR subscribers = '{}'
                """,
            )
            count = int(result.split()[-1]) if result else 0
            logger.info("remove_subscriber_from_all: subscriber=%s deleted=%d rows",
                        subscriber, count)
            return count
