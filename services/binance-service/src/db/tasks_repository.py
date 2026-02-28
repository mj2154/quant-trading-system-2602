"""
任务仓储 - 基于 tasks 表

职责：
- 更新任务状态（pending → processing → completed）
- 更新任务结果
"""

import asyncpg
import json
from datetime import datetime, timezone
from typing import Any


class TasksRepository:
    """任务仓储 - 基于 tasks 表"""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def set_processing(self, task_id: int) -> None:
        """设置任务为处理中"""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE tasks SET status = 'processing', updated_at = $1 WHERE id = $2",
                datetime.now(timezone.utc),
                task_id,
            )

    async def complete(self, task_id: int, result: dict[str, Any] | None) -> None:
        """完成任务

        Args:
            task_id: 任务ID
            result: 任务结果（会自动序列化为JSON字符串存入JSONB字段）
        """
        # 序列化result为JSON字符串（asyncpg需要字符串传给JSONB类型）
        result_json = json.dumps(result) if result is not None else None
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE tasks SET status = 'completed', result = $1, updated_at = $2 WHERE id = $3",
                result_json,
                datetime.now(timezone.utc),
                task_id,
            )

    async def fail(self, task_id: int, error: str) -> None:
        """标记任务失败"""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE tasks SET status = 'failed', result = $1, updated_at = $2 WHERE id = $3",
                json.dumps({"error": error}),
                datetime.now(timezone.utc),
                task_id,
            )

    async def save_account_info(
        self,
        account_type: str,
        data: dict[str, Any],
        update_time: int | None = None,
    ) -> None:
        """保存账户信息（覆盖更新）

        使用 INSERT ... ON CONFLICT 实现 upsert，确保数据一致性。

        Args:
            account_type: 账户类型 (SPOT / FUTURES)
            data: 账户原始数据
            update_time: 币安返回的更新时间
        """
        data_json = json.dumps(data)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO account_info (account_type, data, update_time, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (account_type) DO UPDATE SET
                    data = EXCLUDED.data,
                    update_time = EXCLUDED.update_time,
                    updated_at = EXCLUDED.updated_at
                """,
                account_type,
                data_json,
                update_time,
                datetime.now(timezone.utc),
            )
