"""
实时数据仓储 - 基于 realtime_data 表设计

使用 asyncpg 原生 SQL。
遵循 SUBSCRIPTION_AND_REALTIME_DATA.md 设计：
- INSERT realtime_data → pg_notify('subscription_add')
- DELETE realtime_data → pg_notify('subscription_remove')
- UPDATE realtime_data.data → pg_notify('realtime_update')
- TRUNCATE realtime_data → pg_notify('subscription_clean')
"""

from datetime import datetime
from typing import Any

import asyncpg


class RealtimeDataRepository:
    """实时数据仓储 - 基于 realtime_data 表

    职责：
    - 管理订阅键 (INSERT, DELETE)
    - 查询实时数据 (SELECT)
    - 更新数据内容 (UPDATE)
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def add_subscription(
        self,
        subscription_key: str,
        data_type: str,
        subscriber: str = "api-service",
    ) -> bool:
        """Publish a subscribe task to subscription_tasks.

        The subscription-manager service picks up the task and manages
        the realtime_data table as the sole write authority.

        Returns:
            True if task was created successfully.
        """
        query = """
            INSERT INTO subscription_tasks (type, subscription_key, data_type, subscriber)
            VALUES ('subscribe', $1, $2, $3)
            RETURNING id
        """
        async with self._pool.acquire() as conn:
            task_id = await conn.fetchval(query, subscription_key, data_type, subscriber)
        return task_id is not None

    async def remove_subscription(
        self,
        subscription_key: str,
        subscriber: str = "api-service",
    ) -> bool:
        """Publish an unsubscribe task to subscription_tasks.

        The subscription-manager service picks up the task and manages
        the realtime_data table as the sole write authority.

        Returns:
            True if task was created successfully.
        """
        query = """
            INSERT INTO subscription_tasks (type, subscription_key, subscriber)
            VALUES ('unsubscribe', $1, $2)
            RETURNING id
        """
        async with self._pool.acquire() as conn:
            task_id = await conn.fetchval(query, subscription_key, subscriber)
        return task_id is not None

    async def remove_api_service_subscriptions(self) -> int:
        """Publish unsubscribe tasks for all api-service subscriptions.

        Queries realtime_data for rows where api-service is a subscriber,
        then creates unsubscribe tasks for each. The subscription-manager
        will process these and clean up the realtime_data table.

        Returns:
            Number of unsubscribe tasks created.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT subscription_key FROM realtime_data
                WHERE 'api-service' = ANY(subscribers)
                """
            )
            count = 0
            for row in rows:
                await conn.execute(
                    """
                    INSERT INTO subscription_tasks (type, subscription_key, subscriber)
                    VALUES ('unsubscribe', $1, 'api-service')
                    """,
                    row["subscription_key"],
                )
                count += 1
            return count

    async def get_all_subscriptions(self) -> list[dict[str, Any]]:
        """获取所有订阅

        Returns:
            订阅列表
        """
        query = """
            SELECT subscription_key, data_type, data, event_time, updated_at, subscribers
            FROM realtime_data
            ORDER BY updated_at DESC
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
        return [dict(row) for row in rows]

    async def get_subscription(
        self,
        subscription_key: str,
    ) -> dict[str, Any] | None:
        """获取指定订阅键的数据

        Args:
            subscription_key: 订阅键

        Returns:
            订阅数据或 None
        """
        query = """
            SELECT subscription_key, data_type, data, event_time, updated_at, subscribers
            FROM realtime_data
            WHERE subscription_key = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, subscription_key)
        if row:
            return dict(row)
        return None

    async def update_data(
        self,
        subscription_key: str,
        data: dict[str, Any],
        event_time: datetime | None = None,
    ) -> bool:
        """更新实时数据

        Args:
            subscription_key: 订阅键
            data: 数据内容
            event_time: 事件时间

        Returns:
            是否更新成功
        """
        query = """
            UPDATE realtime_data
            SET data = $1,
                event_time = COALESCE($2, NOW()),
                updated_at = NOW()
            WHERE subscription_key = $3
        """
        async with self._pool.acquire() as conn:
            result: str = await conn.execute(query, data, event_time, subscription_key)
        return result != "UPDATE 0"

    async def truncate_all(self) -> int:
        """清空所有数据（用于API网关启动）

        Returns:
            删除的行数
        """
        query = """
            DELETE FROM realtime_data
            RETURNING id
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
            return len(rows)

    async def get_subscription_count(self) -> int:
        """获取订阅总数

        Returns:
            订阅数量
        """
        query = "SELECT COUNT(*) FROM realtime_data"
        async with self._pool.acquire() as conn:
            result = await conn.fetchval(query)
            return int(result) if result is not None else 0

    async def get_subscriptions_by_type(
        self,
        data_type: str,
    ) -> list[dict[str, Any]]:
        """根据数据类型获取订阅

        Args:
            data_type: 数据类型

        Returns:
            订阅列表
        """
        query = """
            SELECT subscription_key, data_type, data, event_time, updated_at, subscribers
            FROM realtime_data
            WHERE data_type = $1
            ORDER BY updated_at DESC
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, data_type)
        return [dict(row) for row in rows]
