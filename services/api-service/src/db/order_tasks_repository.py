"""
订单任务仓储 - 基于 order_tasks 表

使用 asyncpg 原生 SQL。
设计参考 docs/backend/design/04-trading-orders.md：

- INSERT order_tasks → pg_notify('order_task_new')
- UPDATE order_tasks.status=completed → pg_notify('order_task_completed')

order_tasks 表字段（与 tasks 表一致，增加 request_id 顶层字段）：
- type: 任务类型（order.create, order.cancel, order.query）
- request_id: 请求ID（前端生成，用于关联请求和响应）
- payload: 任务参数（JSON格式，不包含 requestId）
- result: 任务结果
- status: 任务状态（pending, processing, completed, failed）

设计说明：
- request_id 提升到顶层字段，可建索引优化查询
- 贯穿整个数据流：前端 → API → 币安 → 结果推送
"""

import json
import logging
import asyncpg
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OrderTasksRepository:
    """订单任务仓储 - 基于 order_tasks 表

    职责：
    - 创建订单任务 (INSERT)
    - 查询订单任务 (SELECT)
    - 更新订单任务状态和结果 (UPDATE)

    设计说明：
    - order_tasks 表结构与 tasks 表一致
    - request_id 提升到顶层字段，可建索引优化查询
    - payload 不再包含 requestId，从顶层字段获取
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._table_name = "order_tasks"

    async def create_order_task(
        self,
        task_type: str,
        payload: dict[str, Any],
    ) -> int:
        """创建订单任务并返回任务ID

        从 payload 中提取 request_id 存入顶层字段。

        Args:
            task_type: 任务类型 (order.create, order.cancel, order.query)
            payload: 任务参数（从 payload 中提取 request_id）

        Returns:
            任务ID

        Raises:
            ValueError: 参数验证失败
            Exception: 创建失败
        """
        # 参数验证
        if not task_type:
            raise ValueError("task_type cannot be empty")
        if not payload:
            raise ValueError("payload cannot be empty")
        if task_type not in ("order.create", "order.cancel", "order.query"):
            logger.warning(f"Unknown task_type: {task_type}")

        # 从 payload 中提取 request_id（用于顶层字段）
        request_id = payload.pop("requestId", None)

        query = f"""
            INSERT INTO {self._table_name} (type, request_id, payload)
            VALUES ($1, $2, $3)
            RETURNING id
        """
        payload_json = json.dumps(payload)
        async with self._pool.acquire() as conn:
            task_id = await conn.fetchval(query, task_type, request_id, payload_json)

        logger.info(
            f"Created order task: id={task_id}, type={task_type}, request_id={request_id}, "
            f"symbol={payload.get('symbol')}, side={payload.get('side')}"
        )
        return task_id

    async def get_order_task(self, task_id: int) -> Optional[dict[str, Any]]:
        """根据ID获取订单任务

        Args:
            task_id: 任务ID

        Returns:
            任务字典或 None
        """
        query = f"""
            SELECT id, type, request_id, payload, result, status, created_at, updated_at
            FROM {self._table_name}
            WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, task_id)
        if row:
            return dict(row)
        return None

    async def update_order_task_result(
        self,
        task_id: int,
        result: dict[str, Any],
        status: str = "completed",
    ) -> bool:
        """更新订单任务结果和状态

        Args:
            task_id: 任务ID
            result: 任务结果
            status: 任务状态 (默认 completed)

        Returns:
            是否更新成功
        """
        query = f"""
            UPDATE {self._table_name}
            SET result = $1, status = $2, updated_at = NOW()
            WHERE id = $3
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, result, status, task_id)
        return result != "UPDATE 0"

    async def get_order_task_result(self, task_id: int) -> Optional[dict[str, Any]]:
        """获取订单任务结果

        Args:
            task_id: 任务ID

        Returns:
            任务结果或 None
        """
        query = f"""
            SELECT result, status
            FROM {self._table_name}
            WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, task_id)
        if row and row["result"]:
            # JSONB 字段返回 dict 类型，无需再转换
            return row["result"]
        return None

    async def get_pending_count(self) -> int:
        """获取待处理订单任务数量

        Returns:
            待处理任务数
        """
        query = f"""
            SELECT COUNT(*)
            FROM {self._table_name}
            WHERE status = 'pending'
        """
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query)

    async def get_stats(self) -> dict[str, int]:
        """获取订单任务统计

        Returns:
            任务统计字典
        """
        query = f"""
            SELECT status, COUNT(*) as count
            FROM {self._table_name}
            GROUP BY status
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)

        stats: dict[str, int] = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
        for row in rows:
            stats[row["status"]] = row["count"]
        return stats

    async def find_by_request_id(
        self,
        request_id: str,
        task_type: str | None = None,
    ) -> Optional[dict[str, Any]]:
        """根据 request_id 查询订单任务

        直接使用 request_id 顶层字段查询（可建索引，效率高）。

        Args:
            request_id: 请求ID
            task_type: 可选，按任务类型过滤

        Returns:
            任务字典或 None
        """
        if task_type:
            query = f"""
                SELECT id, type, request_id, payload, result, status, created_at, updated_at
                FROM {self._table_name}
                WHERE request_id = $1 AND type = $2
                ORDER BY created_at DESC
                LIMIT 1
            """
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(query, request_id, task_type)
        else:
            query = f"""
                SELECT id, type, request_id, payload, result, status, created_at, updated_at
                FROM {self._table_name}
                WHERE request_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(query, request_id)

        if row:
            return dict(row)
        return None

    async def list_order_tasks(
        self,
        task_type: str | None = None,
        status: str | None = None,
        symbol: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """查询订单任务列表

        Args:
            task_type: 按任务类型过滤
            status: 按状态过滤
            symbol: 按交易对过滤（从 payload 中提取）
            limit: 返回数量限制 (1-1000)
            offset: 分页偏移

        Returns:
            任务列表

        Raises:
            ValueError: 参数验证失败
        """
        # 参数验证
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        conditions = []
        params = []
        param_idx = 1

        if task_type:
            conditions.append(f"type = ${param_idx}")
            params.append(task_type)
            param_idx += 1

        if status:
            conditions.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1

        if symbol:
            conditions.append(f"payload->>'symbol' = ${param_idx}")
            params.append(symbol)
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT id, type, request_id, payload, result, status, created_at, updated_at
            FROM {self._table_name}
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [dict(row) for row in rows]
