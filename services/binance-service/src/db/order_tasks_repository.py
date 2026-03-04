"""
订单任务仓储 - 基于 order_tasks 表

设计参考 docs/backend/design/04-trading-orders.md：
- request_id 提升到顶层字段，可建索引优化查询
- 贯穿整个数据流：前端 → API → 币安 → 结果推送

职责：
- 更新订单任务状态（pending → processing → completed）
- 更新订单任务结果
- 查询待处理的订单任务
- 根据 request_id 查找任务
"""

import asyncpg
import json
from datetime import datetime, timezone
from typing import Any, Optional


class OrderTasksRepository:
    """订单任务仓储 - 基于 order_tasks 表"""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def set_processing(self, task_id: int) -> None:
        """设置任务为处理中"""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE order_tasks SET status = 'processing', updated_at = $1 WHERE id = $2",
                datetime.now(timezone.utc),
                task_id,
            )

    async def complete(self, task_id: int, result: dict[str, Any] | None) -> None:
        """完成任务

        Args:
            task_id: 任务ID
            result: 任务结果（会自动序列化为JSON字符串存入JSONB字段）
        """
        result_json = json.dumps(result) if result is not None else None
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE order_tasks SET status = 'completed', result = $1, updated_at = $2 WHERE id = $3",
                result_json,
                datetime.now(timezone.utc),
                task_id,
            )

    async def fail(self, task_id: int, error: str) -> None:
        """标记任务失败"""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE order_tasks SET status = 'failed', result = $1, updated_at = $2 WHERE id = $3",
                json.dumps({"error": error}),
                datetime.now(timezone.utc),
                task_id,
            )

    async def fetch_pending_tasks(self, limit: int = 10) -> list[dict]:
        """获取待处理的订单任务

        Args:
            limit: 返回数量限制

        Returns:
            任务列表
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, type, request_id, payload, status, created_at
                FROM order_tasks
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT $1
                """,
                limit,
            )
            return [dict(row) for row in rows]

    async def get_task_by_id(self, task_id: int) -> dict | None:
        """根据ID获取任务

        Args:
            task_id: 任务ID

        Returns:
            任务记录或None
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, type, request_id, payload, status, result, created_at FROM order_tasks WHERE id = $1",
                task_id,
            )
            return dict(row) if row else None

    async def find_by_request_id(self, request_id: str) -> Optional[dict]:
        """根据 request_id 查找任务

        直接使用 request_id 顶层字段查询（可建索引，效率高）。

        Args:
            request_id: 请求ID（对应顶层字段 request_id）

        Returns:
            任务记录或None
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, type, request_id, payload, status, result, created_at
                FROM order_tasks
                WHERE request_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                request_id,
            )
            return dict(row) if row else None
