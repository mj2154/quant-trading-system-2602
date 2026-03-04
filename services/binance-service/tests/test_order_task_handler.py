"""
订单任务处理器测试

测试 order_tasks 表的订单任务处理逻辑。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json


class TestOrderTaskHandler:
    """订单任务处理器测试"""

    @pytest.fixture
    def mock_futures_client(self):
        """创建模拟的期货私有客户端"""
        client = MagicMock()
        client.create_order = AsyncMock(return_value={
            "orderId": 12345,
            "clientOrderId": "test_order",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "status": "NEW",
        })
        client.cancel_order = AsyncMock(return_value={
            "orderId": 12345,
            "status": "CANCELED",
        })
        client.get_order = AsyncMock(return_value={
            "orderId": 12345,
            "status": "FILLED",
        })
        return client

    @pytest.fixture
    def mock_spot_client(self):
        """创建模拟的现货私有客户端"""
        client = MagicMock()
        client.create_order = AsyncMock(return_value={
            "orderId": 67890,
            "clientOrderId": "test_order",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "status": "NEW",
        })
        client.cancel_order = AsyncMock(return_value={
            "orderId": 67890,
            "status": "CANCELED",
        })
        client.get_order = AsyncMock(return_value={
            "orderId": 67890,
            "status": "FILLED",
        })
        return client

    @pytest.fixture
    def mock_repo(self):
        """创建模拟的订单任务仓储"""
        repo = MagicMock()
        repo.set_processing = AsyncMock()
        repo.complete = AsyncMock()
        repo.fail = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_handle_order_create_futures(self, mock_futures_client, mock_repo):
        """测试处理期货订单创建任务"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=mock_futures_client,
            spot_client=None,
            order_tasks_repo=mock_repo,
        )

        # 模拟任务载荷
        payload = {
            "task_id": 1,
            "type": "order.create",
            "payload": {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": 0.001,
                "price": 50000,
                "timeInForce": "GTC",
                "marketType": "FUTURES",
            },
        }

        await handler.handle_task(payload)

        # 验证调用
        mock_futures_client.create_order.assert_called_once()
        mock_repo.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_order_create_spot(self, mock_spot_client, mock_repo):
        """测试处理现货订单创建任务"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=None,
            spot_client=mock_spot_client,
            order_tasks_repo=mock_repo,
        )

        payload = {
            "task_id": 1,
            "type": "order.create",
            "payload": {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": 0.001,
                "price": 50000,
                "timeInForce": "GTC",
                "marketType": "SPOT",
            },
        }

        await handler.handle_task(payload)

        mock_spot_client.create_order.assert_called_once()
        mock_repo.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_order_cancel(self, mock_futures_client, mock_repo):
        """测试处理订单取消任务"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=mock_futures_client,
            spot_client=None,
            order_tasks_repo=mock_repo,
        )

        payload = {
            "task_id": 1,
            "type": "order.cancel",
            "payload": {
                "symbol": "BTCUSDT",
                "orderId": 12345,
                "marketType": "FUTURES",
            },
        }

        await handler.handle_task(payload)

        mock_futures_client.cancel_order.assert_called_once()
        mock_repo.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_order_query(self, mock_futures_client, mock_repo):
        """测试处理订单查询任务"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=mock_futures_client,
            spot_client=None,
            order_tasks_repo=mock_repo,
        )

        payload = {
            "task_id": 1,
            "type": "order.query",
            "payload": {
                "symbol": "BTCUSDT",
                "orderId": 12345,
                "marketType": "FUTURES",
            },
        }

        await handler.handle_task(payload)

        mock_futures_client.get_order.assert_called_once()
        mock_repo.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_unknown_type(self, mock_repo):
        """测试处理未知任务类型"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=None,
            spot_client=None,
            order_tasks_repo=mock_repo,
        )

        payload = {
            "task_id": 1,
            "type": "unknown.type",
            "payload": {},
        }

        await handler.handle_task(payload)

        mock_repo.fail.assert_called_once()
