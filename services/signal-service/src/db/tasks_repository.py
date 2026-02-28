"""任务仓储 - 用于信号服务创建K线获取任务。

职责：
- 创建任务 (INSERT tasks)
- 查询任务状态
- 判断任务是否卡死
"""

import json
import logging
from typing import Any

from .database import Database

logger = logging.getLogger(__name__)


class TasksRepository:
    """任务仓储 - 用于信号服务创建和管理任务。"""

    def __init__(self, db: Database) -> None:
        """初始化仓储。

        Args:
            db: 数据库实例。
        """
        self._db = db

    async def create_task(
        self,
        task_type: str,
        payload: dict[str, Any],
    ) -> int:
        """创建任务并返回任务ID。

        Args:
            task_type: 任务类型 (get_klines, get_server_time, get_quotes)
            payload: 任务参数

        Returns:
            任务ID

        Raises:
            Exception: 创建失败
        """
        query = """
            INSERT INTO tasks (type, payload)
            VALUES ($1, $2)
            RETURNING id
        """
        payload_json = json.dumps(payload)
        task_id = await self._db.fetchval(query, task_type, payload_json)
        logger.info(f"Created task: type={task_type} task_id={task_id}")
        return task_id

    async def get_task(self, task_id: int) -> dict[str, Any] | None:
        """根据ID获取任务。

        Args:
            task_id: 任务ID

        Returns:
            任务字典或 None
        """
        query = """
            SELECT id, type, payload, result, status, created_at, updated_at
            FROM tasks
            WHERE id = $1
        """
        row = await self._db.fetchrow(query, task_id)
        if row:
            return dict(row)
        return None

    async def get_task_status(self, task_id: int) -> str | None:
        """获取任务状态。

        Args:
            task_id: 任务ID

        Returns:
            任务状态字符串 (pending, processing, completed, failed) 或 None
        """
        query = """
            SELECT status FROM tasks WHERE id = $1
        """
        row = await self._db.fetchrow(query, task_id)
        if row:
            return row["status"]
        return None
