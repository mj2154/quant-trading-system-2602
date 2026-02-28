"""
订阅状态仓储

使用 asyncpg 原生 SQL。

注意：统一使用 interval 字段，与数据库表结构保持一致。
"""

import asyncpg
from datetime import datetime
from typing import Optional


class SubscriptionRepository:
    """订阅状态仓储"""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def add(
        self,
        client_id: str,
        subscription_key: str,
        exchange: str,
        symbol: str,
        data_type: str,
        interval: Optional[str] = None,  # 统一使用 interval
    ) -> int:
        """添加订阅"""
        query = """
            INSERT INTO subscriptions (
                client_id, subscription_key, exchange, symbol,
                data_type, interval  -- 统一使用 interval
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (client_id, subscription_key) DO UPDATE
            SET status = 'active', subscribed_at = NOW()
            RETURNING id
        """
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                query,
                client_id,
                subscription_key,
                exchange,
                symbol,
                data_type,
                interval,  # 统一使用 interval
            )

    async def remove(self, client_id: str, subscription_key: str) -> bool:
        """移除订阅"""
        query = """
            UPDATE subscriptions
            SET status = 'inactive'
            WHERE client_id = $1 AND subscription_key = $2
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, client_id, subscription_key)
        return result != "UPDATE 0"

    async def remove_all(self, client_id: str) -> int:
        """移除客户端所有订阅"""
        query = """
            UPDATE subscriptions
            SET status = 'inactive'
            WHERE client_id = $1
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, client_id)
        if result.startswith("UPDATE "):
            return int(result.split()[-1])
        return 0

    async def get_by_client(self, client_id: str) -> list[dict]:
        """获取客户端所有订阅"""
        query = """
            SELECT * FROM subscriptions
            WHERE client_id = $1 AND status = 'active'
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, client_id)
        return [dict(row) for row in rows]

    async def get_subscribers(self, subscription_key: str) -> list[str]:
        """获取订阅指定key的所有客户端"""
        query = """
            SELECT client_id FROM subscriptions
            WHERE subscription_key = $1 AND status = 'active'
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, subscription_key)
        return [row["client_id"] for row in rows]

    async def increment_message_count(
        self, client_id: str, subscription_key: str
    ) -> None:
        """增加消息计数"""
        query = """
            UPDATE subscriptions
            SET message_count = message_count + 1,
                last_message_at = NOW()
            WHERE client_id = $1 AND subscription_key = $2
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, client_id, subscription_key)
