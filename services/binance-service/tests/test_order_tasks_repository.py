"""
订单任务仓储测试

测试 order_tasks 表的读写操作。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime, timezone


class TestOrderTasksRepository:
    """订单任务仓储测试"""

    @pytest.fixture
    def mock_pool(self):
        """创建模拟的数据库连接池"""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return pool

    @pytest.mark.asyncio
    async def test_set_processing(self, mock_pool):
        """测试设置任务为处理中"""
        # 先读取现有代码以了解实现
        from db.order_tasks_repository import OrderTasksRepository

        repo = OrderTasksRepository(mock_pool)

        # 执行
        await repo.set_processing(123)

        # 验证
        conn = await mock_pool.acquire().__aenter__()
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_success(self, mock_pool):
        """测试完成任务 - 成功"""
        from db.order_tasks_repository import OrderTasksRepository

        repo = OrderTasksRepository(mock_pool)

        result = {"orderId": 12345, "status": "NEW"}
        await repo.complete(123, result)

        conn = await mock_pool.acquire().__aenter__()
        call_args = conn.execute.call_args
        assert "status = 'completed'" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_fail(self, mock_pool):
        """测试标记任务失败"""
        from db.order_tasks_repository import OrderTasksRepository

        repo = OrderTasksRepository(mock_pool)

        await repo.fail(123, "Insufficient balance")

        conn = await mock_pool.acquire().__aenter__()
        call_args = conn.execute.call_args
        assert "status = 'failed'" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_fetch_pending_tasks(self, mock_pool):
        """测试获取待处理的任务"""
        from db.order_tasks_repository import OrderTasksRepository

        # 模拟返回数据
        mock_cursor = AsyncMock()
        mock_cursor.fetch.return_value = [
            {
                "id": 1,
                "type": "order.create",
                "payload": {"symbol": "BTCUSDT", "side": "BUY"},
                "status": "pending",
                "created_at": datetime.now(timezone.utc),
            }
        ]
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)

        repo = OrderTasksRepository(mock_pool)
        tasks = await repo.fetch_pending_tasks(limit=10)

        assert len(tasks) == 1
        assert tasks[0]["type"] == "order.create"
