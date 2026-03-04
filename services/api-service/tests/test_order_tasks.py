"""
订单任务仓储测试

测试 OrderTasksRepository 对 order_tasks 表的操作。
遵循 TDD 流程：先编写测试，再实现功能。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import json


class TestOrderTasksRepository:
    """订单任务仓储测试类"""

    def _create_mock_pool(self):
        """创建正确配置的 mock pool - 返回异步上下文管理器"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()

        # 模拟 asyncpg.Pool.acquire() 返回的异步上下文管理器
        mock_acquire_cm = MagicMock()
        mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_cm.__aexit__ = AsyncMock()

        mock_pool.acquire = MagicMock(return_value=mock_acquire_cm)

        return mock_pool, mock_conn

    @pytest.mark.asyncio
    async def test_create_order_task(self):
        """测试创建订单任务"""
        from src.db.order_tasks_repository import OrderTasksRepository

        mock_pool, mock_conn = self._create_mock_pool()
        mock_conn.fetchval = AsyncMock(return_value=123)

        repo = OrderTasksRepository(mock_pool)

        task_id = await repo.create_order_task(
            task_type="order.create",
            payload={
                "requestId": "req_test_001",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": 0.002,
                "price": 50000.0,
            },
        )

        assert task_id == 123

    @pytest.mark.asyncio
    async def test_get_order_task(self):
        """测试获取订单任务"""
        from src.db.order_tasks_repository import OrderTasksRepository

        mock_pool, mock_conn = self._create_mock_pool()

        mock_row = {
            "id": 123,
            "type": "order.create",
            "payload": {"requestId": "req_test_001", "symbol": "BTCUSDT"},
            "result": {"orderId": "456", "status": "NEW"},
            "status": "completed",
            "created_at": "2026-03-01T00:00:00Z",
            "updated_at": "2026-03-01T00:01:00Z",
        }
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        repo = OrderTasksRepository(mock_pool)

        result = await repo.get_order_task(123)

        assert result is not None
        assert result["id"] == 123
        assert result["type"] == "order.create"

    @pytest.mark.asyncio
    async def test_get_order_task_not_found(self):
        """测试获取不存在的订单任务"""
        from src.db.order_tasks_repository import OrderTasksRepository

        mock_pool, mock_conn = self._create_mock_pool()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        repo = OrderTasksRepository(mock_pool)

        result = await repo.get_order_task(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_order_task_result(self):
        """测试更新订单任务结果"""
        from src.db.order_tasks_repository import OrderTasksRepository

        mock_pool, mock_conn = self._create_mock_pool()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        repo = OrderTasksRepository(mock_pool)

        result = await repo.update_order_task_result(
            task_id=123,
            result={"orderId": "456", "status": "FILLED"},
            status="completed",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_get_pending_count(self):
        """测试获取待处理订单任务数量"""
        from src.db.order_tasks_repository import OrderTasksRepository

        mock_pool, mock_conn = self._create_mock_pool()
        mock_conn.fetchval = AsyncMock(return_value=5)

        repo = OrderTasksRepository(mock_pool)

        count = await repo.get_pending_count()

        assert count == 5

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """测试获取订单任务统计"""
        from src.db.order_tasks_repository import OrderTasksRepository

        mock_pool, mock_conn = self._create_mock_pool()

        mock_rows = [
            {"status": "pending", "count": 5},
            {"status": "completed", "count": 10},
            {"status": "failed", "count": 2},
        ]
        mock_conn.fetch = AsyncMock(return_value=mock_rows)

        repo = OrderTasksRepository(mock_pool)

        stats = await repo.get_stats()

        assert stats["pending"] == 5
        assert stats["completed"] == 10
        assert stats["failed"] == 2
        assert stats["processing"] == 0  # 默认值

    @pytest.mark.asyncio
    async def test_find_by_request_id(self):
        """测试根据 requestId 查询订单任务"""
        from src.db.order_tasks_repository import OrderTasksRepository

        mock_pool, mock_conn = self._create_mock_pool()

        mock_row = {
            "id": 123,
            "type": "order.create",
            "payload": {"requestId": "req_abc123", "symbol": "BTCUSDT"},
            "result": {"orderId": "456"},
            "status": "completed",
            "created_at": "2026-03-01T00:00:00Z",
            "updated_at": "2026-03-01T00:01:00Z",
        }
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        repo = OrderTasksRepository(mock_pool)

        result = await repo.find_by_request_id("req_abc123")

        assert result is not None
        assert result["payload"]["requestId"] == "req_abc123"

    @pytest.mark.asyncio
    async def test_find_by_request_id_with_type(self):
        """测试根据 requestId 和类型查询订单任务"""
        from src.db.order_tasks_repository import OrderTasksRepository

        mock_pool, mock_conn = self._create_mock_pool()

        mock_row = {
            "id": 123,
            "type": "order.create",
            "payload": {"requestId": "req_abc123", "symbol": "BTCUSDT"},
            "result": {"orderId": "456"},
            "status": "completed",
            "created_at": "2026-03-01T00:00:00Z",
            "updated_at": "2026-03-01T00:01:00Z",
        }
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        repo = OrderTasksRepository(mock_pool)

        result = await repo.find_by_request_id("req_abc123", "order.create")

        assert result is not None
        mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_order_tasks(self):
        """测试查询订单任务列表"""
        from src.db.order_tasks_repository import OrderTasksRepository

        mock_pool, mock_conn = self._create_mock_pool()

        mock_rows = [
            {
                "id": 1,
                "type": "order.create",
                "payload": {"requestId": "req_001", "symbol": "BTCUSDT"},
                "result": {"orderId": "1"},
                "status": "completed",
                "created_at": "2026-03-01T00:00:00Z",
                "updated_at": "2026-03-01T00:01:00Z",
            },
            {
                "id": 2,
                "type": "order.cancel",
                "payload": {"requestId": "req_002", "symbol": "BTCUSDT"},
                "result": None,
                "status": "pending",
                "created_at": "2026-03-01T00:02:00Z",
                "updated_at": "2026-03-01T00:02:00Z",
            },
        ]
        mock_conn.fetch = AsyncMock(return_value=mock_rows)

        repo = OrderTasksRepository(mock_pool)

        results = await repo.list_order_tasks(limit=10)

        assert len(results) == 2
        assert results[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_list_order_tasks_with_filters(self):
        """测试带过滤条件查询订单任务列表"""
        from src.db.order_tasks_repository import OrderTasksRepository

        mock_pool, mock_conn = self._create_mock_pool()
        mock_conn.fetch = AsyncMock(return_value=[])

        repo = OrderTasksRepository(mock_pool)

        # 使用类型过滤
        await repo.list_order_tasks(task_type="order.create", limit=5)

        # 使用状态过滤
        await repo.list_order_tasks(status="completed", limit=5)

        # 使用交易对过滤
        await repo.list_order_tasks(symbol="BTCUSDT", limit=5)

        # 验证 fetch 被调用多次
        assert mock_conn.fetch.call_count >= 3


class TestTaskRouterOrderHandling:
    """TaskRouter 订单处理测试类"""

    @pytest.mark.asyncio
    async def test_handle_create_order(self):
        """测试处理 CREATE_ORDER 请求"""
        from src.gateway.task_router import TaskRouter
        from src.gateway.subscription_manager import SubscriptionManager
        from src.gateway.client_manager import ClientManager

        subscription_manager = MagicMock(spec=SubscriptionManager)
        client_manager = MagicMock(spec=ClientManager)
        client_manager.send = AsyncMock()

        mock_order_tasks_repo = MagicMock()
        mock_order_tasks_repo.create_order_task = AsyncMock(return_value=1)

        router = TaskRouter(
            subscription_manager=subscription_manager,
            client_manager=client_manager,
        )
        router.set_order_tasks_repository(mock_order_tasks_repo)

        request = {
            "protocolVersion": "2.0",
            "type": "CREATE_ORDER",
            "requestId": "req_order_001",
            "timestamp": 1704067200000,
            "data": {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": 0.002,
                "price": 50000.0,
                "timeInForce": "GTC",
            },
        }

        result = await router.handle("client_001", request)

        mock_order_tasks_repo.create_order_task.assert_called_once()

        assert client_manager.send.call_count >= 1
        calls = client_manager.send.call_args_list
        ack_msg = calls[0][0][1]
        assert ack_msg["type"] == "ACK"
        assert ack_msg["requestId"] == "req_order_001"

    @pytest.mark.asyncio
    async def test_handle_get_order(self):
        """测试处理 GET_ORDER 请求"""
        from src.gateway.task_router import TaskRouter
        from src.gateway.subscription_manager import SubscriptionManager
        from src.gateway.client_manager import ClientManager

        subscription_manager = MagicMock(spec=SubscriptionManager)
        client_manager = MagicMock(spec=ClientManager)
        client_manager.send = AsyncMock()

        mock_order_tasks_repo = MagicMock()
        mock_order_tasks_repo.create_order_task = AsyncMock(return_value=1)

        router = TaskRouter(
            subscription_manager=subscription_manager,
            client_manager=client_manager,
        )
        router.set_order_tasks_repository(mock_order_tasks_repo)

        request = {
            "protocolVersion": "2.0",
            "type": "GET_ORDER",
            "requestId": "req_order_002",
            "timestamp": 1704067200000,
            "data": {
                "symbol": "BTCUSDT",
                "orderId": "123456",
            },
        }

        await router.handle("client_001", request)

        call_args = mock_order_tasks_repo.create_order_task.call_args
        assert call_args[1]["task_type"] == "order.query"

    @pytest.mark.asyncio
    async def test_handle_cancel_order(self):
        """测试处理 CANCEL_ORDER 请求"""
        from src.gateway.task_router import TaskRouter
        from src.gateway.subscription_manager import SubscriptionManager
        from src.gateway.client_manager import ClientManager

        subscription_manager = MagicMock(spec=SubscriptionManager)
        client_manager = MagicMock(spec=ClientManager)
        client_manager.send = AsyncMock()

        mock_order_tasks_repo = MagicMock()
        mock_order_tasks_repo.create_order_task = AsyncMock(return_value=1)

        router = TaskRouter(
            subscription_manager=subscription_manager,
            client_manager=client_manager,
        )
        router.set_order_tasks_repository(mock_order_tasks_repo)

        request = {
            "protocolVersion": "2.0",
            "type": "CANCEL_ORDER",
            "requestId": "req_order_004",
            "timestamp": 1704067200000,
            "data": {
                "symbol": "BTCUSDT",
                "orderId": "123456",
            },
        }

        await router.handle("client_001", request)

        call_args = mock_order_tasks_repo.create_order_task.call_args
        assert call_args[1]["task_type"] == "order.cancel"

    @pytest.mark.asyncio
    async def test_create_order_payload_contains_request_id(self):
        """测试创建订单时 payload 包含 requestId"""
        from src.gateway.task_router import TaskRouter
        from src.gateway.subscription_manager import SubscriptionManager
        from src.gateway.client_manager import ClientManager

        subscription_manager = MagicMock(spec=SubscriptionManager)
        client_manager = MagicMock(spec=ClientManager)
        client_manager.send = AsyncMock()

        mock_order_tasks_repo = MagicMock()
        mock_order_tasks_repo.create_order_task = AsyncMock(return_value=1)

        router = TaskRouter(
            subscription_manager=subscription_manager,
            client_manager=client_manager,
        )
        router.set_order_tasks_repository(mock_order_tasks_repo)

        request = {
            "protocolVersion": "2.0",
            "type": "CREATE_ORDER",
            "requestId": "req_order_006",
            "timestamp": 1704067200000,
            "data": {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": 0.002,
                "price": 50000.0,
            },
        }

        await router.handle("client_001", request)

        call_args = mock_order_tasks_repo.create_order_task.call_args
        assert call_args is not None
        payload = call_args[1]["payload"]
        assert "requestId" in payload
        assert payload["requestId"] == "req_order_006"

    @pytest.mark.asyncio
    async def test_create_order_adds_market_type(self):
        """测试创建订单时自动添加 marketType"""
        from src.gateway.task_router import TaskRouter
        from src.gateway.subscription_manager import SubscriptionManager
        from src.gateway.client_manager import ClientManager

        subscription_manager = MagicMock(spec=SubscriptionManager)
        client_manager = MagicMock(spec=ClientManager)
        client_manager.send = AsyncMock()

        mock_order_tasks_repo = MagicMock()
        mock_order_tasks_repo.create_order_task = AsyncMock(return_value=1)

        router = TaskRouter(
            subscription_manager=subscription_manager,
            client_manager=client_manager,
        )
        router.set_order_tasks_repository(mock_order_tasks_repo)

        request = {
            "protocolVersion": "2.0",
            "type": "CREATE_ORDER",
            "requestId": "req_order_007",
            "timestamp": 1704067200000,
            "data": {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": 0.002,
            },
        }

        await router.handle("client_001", request)

        call_args = mock_order_tasks_repo.create_order_task.call_args
        payload = call_args[1]["payload"]
        assert "marketType" in payload
        assert payload["marketType"] == "FUTURES"

    @pytest.mark.asyncio
    async def test_order_tasks_repository_not_initialized(self):
        """测试订单仓储未初始化时返回错误"""
        from src.gateway.task_router import TaskRouter
        from src.gateway.subscription_manager import SubscriptionManager
        from src.gateway.client_manager import ClientManager

        subscription_manager = MagicMock(spec=SubscriptionManager)
        client_manager = MagicMock(spec=ClientManager)
        client_manager.send = AsyncMock()

        router = TaskRouter(
            subscription_manager=subscription_manager,
            client_manager=client_manager,
        )

        request = {
            "protocolVersion": "2.0",
            "type": "CREATE_ORDER",
            "requestId": "req_order_009",
            "timestamp": 1704067200000,
            "data": {
                "symbol": "BTCUSDT",
                "side": "BUY",
            },
        }

        await router.handle("client_001", request)

        assert client_manager.send.call_count >= 2

        calls = client_manager.send.call_args_list

        ack_msg = calls[0][0][1]
        assert ack_msg["type"] == "ACK"

        error_msg = calls[1][0][1]
        assert error_msg["type"] == "ERROR"
        assert error_msg["data"]["errorCode"] == "ORDER_TASKS_REPOSITORY_NOT_SET"

    @pytest.mark.asyncio
    async def test_handle_list_orders(self):
        """测试处理 LIST_ORDERS 请求"""
        from src.gateway.task_router import TaskRouter
        from src.gateway.subscription_manager import SubscriptionManager
        from src.gateway.client_manager import ClientManager

        subscription_manager = MagicMock(spec=SubscriptionManager)
        client_manager = MagicMock(spec=ClientManager)
        client_manager.send = AsyncMock()

        mock_order_tasks_repo = MagicMock()
        mock_order_tasks_repo.create_order_task = AsyncMock(return_value=1)

        router = TaskRouter(
            subscription_manager=subscription_manager,
            client_manager=client_manager,
        )
        router.set_order_tasks_repository(mock_order_tasks_repo)

        request = {
            "protocolVersion": "2.0",
            "type": "LIST_ORDERS",
            "requestId": "req_order_010",
            "timestamp": 1704067200000,
            "data": {
                "symbol": "BTCUSDT",
                "limit": 100,
            },
        }

        await router.handle("client_001", request)

        mock_order_tasks_repo.create_order_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_get_open_orders(self):
        """测试处理 GET_OPEN_ORDERS 请求"""
        from src.gateway.task_router import TaskRouter
        from src.gateway.subscription_manager import SubscriptionManager
        from src.gateway.client_manager import ClientManager

        subscription_manager = MagicMock(spec=SubscriptionManager)
        client_manager = MagicMock(spec=ClientManager)
        client_manager.send = AsyncMock()

        mock_order_tasks_repo = MagicMock()
        mock_order_tasks_repo.create_order_task = AsyncMock(return_value=1)

        router = TaskRouter(
            subscription_manager=subscription_manager,
            client_manager=client_manager,
        )
        router.set_order_tasks_repository(mock_order_tasks_repo)

        request = {
            "protocolVersion": "2.0",
            "type": "GET_OPEN_ORDERS",
            "requestId": "req_order_011",
            "timestamp": 1704067200000,
            "data": {
                "symbol": "BTCUSDT",
            },
        }

        await router.handle("client_001", request)

        mock_order_tasks_repo.create_order_task.assert_called_once()
