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

    async def insert_subscription(
        self, subscription_key: str, data_type: str, data: dict[str, Any] | None = None
    ) -> int:
        """Insert a new subscription.

        如果订阅已存在，追加 signal-service 到 subscribers 数组。

        Args:
            subscription_key: The subscription key.
            data_type: The data type (KLINE, QUOTES, TRADE).
            data: Initial data (optional).

        Returns:
            Inserted/Updated record ID.
        """
        # 先尝试 UPDATE：追加 subscribers（确保 idempotent）
        update_result = await self._db.execute(
            """
            UPDATE realtime_data
            SET subscribers = ARRAY_APPEND(
                ARRAY_REMOVE(subscribers, $1),
                $1
            ),
            updated_at = NOW()
            WHERE subscription_key = $2
            """,
            self.SUBSCRIBER_ID,
            subscription_key,
        )

        # 检查是否更新了行
        if "UPDATE 1" in update_result:
            row = await self._db.fetchrow(
                "SELECT id FROM realtime_data WHERE subscription_key = $1 ORDER BY created_at DESC LIMIT 1",
                subscription_key,
            )
            if row:
                return row["id"]

        # UPDATE 0 行（记录不存在），执行 INSERT
        insert_result = await self._db.execute(
            """
            INSERT INTO realtime_data (subscription_key, data_type, data, subscribers)
            VALUES ($1, $2, $3, ARRAY[$4])
            RETURNING id
            """,
            subscription_key,
            data_type,
            json.dumps(data) if data else "{}",
            self.SUBSCRIBER_ID,
        )

        if insert_result and "INSERT" in insert_result:
            row = await self._db.fetchrow(
                "SELECT id FROM realtime_data WHERE subscription_key = $1 ORDER BY created_at DESC LIMIT 1",
                subscription_key,
            )
            if row:
                return row["id"]

        return 0

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
        """Remove signal-service from subscription.

        If subscribers array becomes empty, delete the row.

        Args:
            subscription_key: The subscription key to remove from.

        Returns:
            True if removed successfully, False if not found.
        """
        # First, remove signal-service from the subscribers array
        result = await self._db.execute(
            """
            UPDATE realtime_data
            SET subscribers = ARRAY_REMOVE(subscribers, $1),
                updated_at = NOW()
            WHERE subscription_key = $2
            """,
            self.SUBSCRIBER_ID,
            subscription_key,
        )

        # Check if any row was updated
        if "UPDATE 0" in result:
            return False

        # Check if subscribers array is now empty, if so delete the row
        row = await self._db.fetchrow(
            """
            SELECT subscribers FROM realtime_data WHERE subscription_key = $1
            """,
            subscription_key,
        )

        if row and (row["subscribers"] is None or len(row["subscribers"]) == 0):
            await self._db.execute(
                "DELETE FROM realtime_data WHERE subscription_key = $1",
                subscription_key,
            )
            logger.info(
                "[REPO] Deleted empty subscription: %s",
                subscription_key,
            )
        else:
            logger.info(
                "[REPO] Removed signal-service from subscription: %s (remaining: %s)",
                subscription_key,
                row["subscribers"] if row else "N/A",
            )

        return True
