"""Repository for realtime_data table operations."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from .database import Database

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RealtimeDataRecord:
    """Realtime data record."""

    id: int
    subscription_key: str
    data_type: str
    data: dict[str, Any]
    event_time: Any  # timestamptz
    created_at: Any  # timestamptz
    updated_at: Any  # timestamptz
    subscribers: list[str] | None = None


class RealtimeDataRepository:
    """Repository for realtime_data table operations."""

    SUBSCRIBER_ID = "signal-service"  # 订阅源标识

    def __init__(self, db: Database) -> None:
        """Initialize repository.

        Args:
            db: Database instance.
        """
        self._db = db

    async def get_by_subscription_key(
        self, subscription_key: str
    ) -> RealtimeDataRecord | None:
        """Get realtime data by subscription key.

        Args:
            subscription_key: The subscription key to query.

        Returns:
            Record if found, None otherwise.
        """
        row = await self._db.fetchrow(
            """
            SELECT id, subscription_key, data_type, data, event_time, created_at, updated_at, subscribers
            FROM realtime_data
            WHERE subscription_key = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            subscription_key,
        )
        if row is None:
            return None
        return RealtimeDataRecord(**row)

    async def get_kline_subscriptions(self) -> list[RealtimeDataRecord]:
        """Get all KLINE type subscriptions.

        Returns:
            List of KLINE subscription records.
        """
        rows = await self._db.fetch(
            """
            SELECT DISTINCT ON (subscription_key) id, subscription_key, data_type, data, event_time, created_at, updated_at, subscribers
            FROM realtime_data
            WHERE data_type = 'KLINE'
            ORDER BY subscription_key, created_at DESC
            """
        )
        return [RealtimeDataRecord(**row) for row in rows]

    async def get_subscriptions_by_subscriber(self, subscriber: str) -> list[RealtimeDataRecord]:
        """Get all subscriptions for a specific subscriber.

        Args:
            subscriber: The subscriber ID to filter by.

        Returns:
            List of subscription records where the subscriber is in the subscribers array.
        """
        rows = await self._db.fetch(
            """
            SELECT id, subscription_key, data_type, data, event_time, created_at, updated_at, subscribers
            FROM realtime_data
            WHERE $1 = ANY(subscribers)
            ORDER BY subscription_key
            """,
            subscriber,
        )
        return [RealtimeDataRecord(**row) for row in rows]

    async def insert_subscription(
        self, subscription_key: str, data_type: str, data: dict[str, Any] | None = None
    ) -> int:
        """Publish a subscribe task to subscription_tasks.

        The subscription-manager service picks up the task and manages
        the realtime_data table as the sole write authority.

        Returns:
            Task ID if created successfully, 0 otherwise.
        """
        task_id = await self._db.fetchval(
            """
            INSERT INTO subscription_tasks (type, subscription_key, data_type, subscriber)
            VALUES ('subscribe', $1, $2, $3)
            RETURNING id
            """,
            subscription_key,
            data_type,
            self.SUBSCRIBER_ID,
        )
        return task_id if task_id else 0

    async def get_all(self) -> list[RealtimeDataRecord]:
        """Get all realtime data records.

        Returns:
            List of all records.
        """
        rows = await self._db.fetch(
            """
            SELECT DISTINCT ON (subscription_key) id, subscription_key, data_type, data, event_time, created_at, updated_at, subscribers
            FROM realtime_data
            ORDER BY subscription_key, created_at DESC
            """
        )
        return [RealtimeDataRecord(**row) for row in rows]

    async def get_klines_history(
        self,
        symbol: str,
        interval: str,
        limit: int = 280,
    ) -> list[dict[str, Any]]:
        """Fetch latest klines from klines_history table.

        Args:
            symbol: Trading pair symbol (e.g., "BINANCE:BTCUSDT").
            interval: K-line interval in TV format (e.g., "1", "5", "60").
            limit: Number of klines to fetch (default 280).

        Returns:
            List of kline records in database raw format, ordered by open_time ascending.
        """
        rows = await self._db.fetch(
            """
            SELECT
                id, symbol, interval, open_time, close_time,
                open_price, high_price, low_price, close_price,
                volume, quote_volume, number_of_trades,
                taker_buy_base_volume, taker_buy_quote_volume,
                created_at
            FROM klines_history
            WHERE symbol = $1 AND interval = $2
            ORDER BY open_time DESC
            LIMIT $3
            """,
            symbol,
            interval,
            limit,
        )

        # Reverse to get chronological order (oldest first)
        rows_list = [dict(row) for row in rows]
        rows_list.reverse()
        return rows_list

    async def remove_subscription(self, subscription_key: str) -> bool:
        """Publish an unsubscribe task to subscription_tasks.

        The subscription-manager service picks up the task and manages
        the realtime_data table as the sole write authority.

        Returns:
            True if task was created successfully.
        """
        task_id = await self._db.fetchval(
            """
            INSERT INTO subscription_tasks (type, subscription_key, subscriber)
            VALUES ('unsubscribe', $1, $2)
            RETURNING id
            """,
            subscription_key,
            self.SUBSCRIBER_ID,
        )
        return task_id is not None
