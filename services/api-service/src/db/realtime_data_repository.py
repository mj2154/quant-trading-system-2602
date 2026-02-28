"""
实时数据仓储 - 基于 realtime_data 表设计

使用 asyncpg 原生 SQL。
遵循 SUBSCRIPTION_AND_REALTIME_DATA.md 设计：
- INSERT realtime_data → pg_notify('subscription.add')
- DELETE realtime_data → pg_notify('subscription.remove')
- UPDATE realtime_data.data → pg_notify('realtime.update')
- TRUNCATE realtime_data → pg_notify('subscription.clean')
"""

import asyncpg
from datetime import datetime
from typing import Optional, List, Dict, Any


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
        """添加订阅键

        Args:
            subscription_key: 订阅键
            data_type: 数据类型 (KLINE, QUOTES, TRADE)
            subscriber: 订阅源标识

        Returns:
            是否添加成功（新增 subscriber 返回 True，已存在返回 False）
        """
        # 使用 ON CONFLICT (subscription_key) 实现 UPSERT
        # 使用 ARRAY_REMOVE + ARRAY_PREPEND 确保不重复添加 subscriber
        query = """
            INSERT INTO realtime_data (subscription_key, data_type, data, subscribers)
            VALUES ($1, $2, '{}'::jsonb, ARRAY[$3])
            ON CONFLICT (subscription_key)
            DO UPDATE SET
                subscribers = ARRAY_PREPEND($3, ARRAY_REMOVE(realtime_data.subscribers, $3))
            RETURNING (xmax = 0) as is_insert;
        """
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval(query, subscription_key, data_type, subscriber)
            return result  # True = INSERT (新行), False = UPDATE (已存在)
        except asyncpg.UniqueViolationError:
            return False  # 已存在

    async def remove_subscription(
        self,
        subscription_key: str,
        subscriber: str = "api-service",
    ) -> bool:
        """移除订阅键

        Args:
            subscription_key: 订阅键
            subscriber: 订阅源标识

        Returns:
            是否删除成功
        """
        # 先从数组中移除订阅者
        query = """
            UPDATE realtime_data
            SET subscribers = ARRAY_REMOVE(subscribers, $2)
            WHERE subscription_key = $1
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, subscription_key, subscriber)

        # 如果订阅者列表为空，则删除该行
        if not await self.has_subscribers(subscription_key):
            return await self._delete_by_key(subscription_key)
        return True

    async def _delete_by_key(self, subscription_key: str) -> bool:
        """根据订阅键删除数据

        Args:
            subscription_key: 订阅键

        Returns:
            是否删除成功
        """
        query = "DELETE FROM realtime_data WHERE subscription_key = $1"
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, subscription_key)
        return result != "DELETE 0"

    async def has_subscribers(self, subscription_key: str) -> bool:
        """检查是否还有其他订阅源

        Args:
            subscription_key: 订阅键

        Returns:
            是否存在订阅者
        """
        query = """
            SELECT EXISTS(
                SELECT 1 FROM realtime_data
                WHERE subscription_key = $1
                  AND cardinality(subscribers) > 0
            )
        """
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, subscription_key)

    async def remove_api_service_subscriptions(self) -> int:
        """清理 api-service 创建的所有订阅（保留其他订阅源的数据）

        对于只有 api-service 的记录，执行 DELETE
        对于有多个订阅者的记录，从数组中移除 api-service

        Returns:
            清理的记录数
        """
        async with self._pool.acquire() as conn:
            # 先从数组中移除 api-service
            await conn.execute("""
                UPDATE realtime_data
                SET subscribers = ARRAY_REMOVE(subscribers, 'api-service')
                WHERE 'api-service' = ANY(subscribers)
            """)

            # 删除 subscribers 为空或只有 api-service 的记录
            rows = await conn.fetch("""
                DELETE FROM realtime_data
                WHERE subscribers IS NULL
                   OR subscribers = '{}'
                   OR subscribers = ARRAY['api-service']
                RETURNING id
            """)
            return len(rows)

    async def get_all_subscriptions(self) -> List[Dict[str, Any]]:
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
    ) -> Optional[Dict[str, Any]]:
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
        data: Dict[str, Any],
        event_time: Optional[datetime] = None,
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
            result = await conn.execute(query, data, event_time, subscription_key)
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
            return await conn.fetchval(query)

    async def get_subscriptions_by_type(
        self,
        data_type: str,
    ) -> List[Dict[str, Any]]:
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
