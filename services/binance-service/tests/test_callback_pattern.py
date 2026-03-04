"""
回调模式测试 - WS客户端回调模式

测试WS客户端的回调模式实现：
- 移除 _pending_requests，使用回调处理响应
- set_response_callback 方法
- 回调收到响应后调用处理方法
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json


class TestFuturesWSClientCallback:
    """期货WS客户端回调模式测试"""

    @pytest.fixture
    def mock_dependencies(self):
        """创建模拟依赖"""
        with patch('clients.futures_private_ws_client.connect', new_callable=AsyncMock) as mock_connect, \
             patch('clients.futures_private_ws_client.Ed25519Signer') as mock_signer:
            # 模拟签名器
            signer_instance = MagicMock()
            signer_instance.sign.return_value = "mock_signature"
            mock_signer.return_value = signer_instance

            yield {
                "connect": mock_connect,
                "signer": signer_instance,
            }

    @pytest.mark.asyncio
    async def test_set_response_callback(self, mock_dependencies):
        """测试设置响应回调"""
        from clients.futures_private_ws_client import BinanceFuturesPrivateWSClient

        # 创建一个不连接的客户端
        client = BinanceFuturesPrivateWSClient(
            api_key="test_key",
            private_key_pem=b"test_key",
            use_testnet=True,
        )

        # 测试回调设置
        callback = AsyncMock()
        client.set_response_callback(callback)

        assert client._response_callback == callback

    @pytest.mark.asyncio
    async def test_handle_message_calls_callback(self, mock_dependencies):
        """测试收到响应消息时调用回调"""
        from clients.futures_private_ws_client import BinanceFuturesPrivateWSClient

        client = BinanceFuturesPrivateWSClient(
            api_key="test_key",
            private_key_pem=b"test_key",
            use_testnet=True,
        )

        # 设置回调
        callback = AsyncMock()
        client.set_response_callback(callback)

        # 模拟收到响应消息
        response_message = {
            "id": "test-request-id",
            "status": 200,
            "result": {"orderId": 12345},
        }

        await client._handle_message(response_message)

        # 验证回调被调用
        callback.assert_called_once_with("test-request-id", response_message)


class TestSpotWSClientCallback:
    """现货WS客户端回调模式测试"""

    @pytest.fixture
    def mock_dependencies(self):
        """创建模拟依赖"""
        with patch('clients.spot_private_ws_client.connect', new_callable=AsyncMock) as mock_connect, \
             patch('clients.spot_private_ws_client.Ed25519Signer') as mock_signer:
            # 模拟签名器
            signer_instance = MagicMock()
            signer_instance.sign.return_value = "mock_signature"
            mock_signer.return_value = signer_instance

            yield {
                "connect": mock_connect,
                "signer": signer_instance,
            }

    @pytest.mark.asyncio
    async def test_set_response_callback(self, mock_dependencies):
        """测试设置响应回调"""
        from clients.spot_private_ws_client import BinanceSpotPrivateWSClient

        client = BinanceSpotPrivateWSClient(
            api_key="test_key",
            private_key_pem=b"test_key",
        )

        # 测试回调设置
        callback = AsyncMock()
        client.set_response_callback(callback)

        assert client._response_callback == callback

    @pytest.mark.asyncio
    async def test_handle_message_calls_callback(self, mock_dependencies):
        """测试收到响应消息时调用回调"""
        from clients.spot_private_ws_client import BinanceSpotPrivateWSClient

        client = BinanceSpotPrivateWSClient(
            api_key="test_key",
            private_key_pem=b"test_key",
        )

        # 设置回调
        callback = AsyncMock()
        client.set_response_callback(callback)

        # 模拟收到响应消息
        response_message = {
            "id": "test-request-id",
            "status": 200,
            "result": {"orderId": 67890},
        }

        await client._handle_message(response_message)

        # 验证回调被调用
        callback.assert_called_once_with("test-request-id", response_message)


class TestOrderTasksRepositoryFindByRequestId:
    """订单任务仓储 find_by_request_id 测试"""

    @pytest.fixture
    def mock_pool(self):
        """创建模拟的数据库连接池"""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return pool

    @pytest.mark.asyncio
    async def test_find_by_request_id(self, mock_pool):
        """测试根据 requestId 查找任务"""
        from db.order_tasks_repository import OrderTasksRepository

        # 模拟返回数据
        mock_cursor = AsyncMock()
        mock_cursor.fetchrow.return_value = {
            "id": 1,
            "type": "order.create",
            "payload": {"symbol": "BTCUSDT", "side": "BUY", "requestId": "req-123"},
            "status": "pending",
            "created_at": None,
        }
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)

        repo = OrderTasksRepository(mock_pool)
        task = await repo.find_by_request_id("req-123")

        assert task is not None
        assert task["id"] == 1
        # 验证查询语句包含 requestId 条件
        call_args = mock_cursor.fetchrow.call_args
        assert "requestId" in call_args[0][0] or "$1" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_find_by_request_id_not_found(self, mock_pool):
        """测试根据不存在的 requestId 查找任务返回 None"""
        from db.order_tasks_repository import OrderTasksRepository

        # 模拟返回 None
        mock_cursor = AsyncMock()
        mock_cursor.fetchrow.return_value = None
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)

        repo = OrderTasksRepository(mock_pool)
        task = await repo.find_by_request_id("non-existent")

        assert task is None


class TestOrderTaskHandlerCallback:
    """订单任务处理器回调模式测试"""

    @pytest.fixture
    def mock_futures_client(self):
        """创建模拟的期货私有客户端"""
        client = MagicMock()
        client.set_response_callback = MagicMock()
        client.send_request = AsyncMock()
        return client

    @pytest.fixture
    def mock_spot_client(self):
        """创建模拟的现货私有客户端"""
        client = MagicMock()
        client.set_response_callback = MagicMock()
        client.send_request = AsyncMock()
        return client

    @pytest.fixture
    def mock_repo(self):
        """创建模拟的订单任务仓储"""
        repo = MagicMock()
        repo.set_processing = AsyncMock()
        repo.complete = AsyncMock()
        repo.fail = AsyncMock()
        repo.find_by_request_id = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_handler_sets_callback_on_futures_client(self, mock_futures_client, mock_repo):
        """测试处理器在初始化时设置期货客户端回调"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=mock_futures_client,
            spot_client=None,
            order_tasks_repo=mock_repo,
        )

        # 验证设置了回调
        mock_futures_client.set_response_callback.assert_called_once()
        # 获取设置的回调函数
        callback = mock_futures_client.set_response_callback.call_args[0][0]
        assert callable(callback)

    @pytest.mark.asyncio
    async def test_handler_sets_callback_on_spot_client(self, mock_spot_client, mock_repo):
        """测试处理器在初始化时设置现货客户端回调"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=None,
            spot_client=mock_spot_client,
            order_tasks_repo=mock_repo,
        )

        # 验证设置了回调
        mock_spot_client.set_response_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_futures_response_success(self, mock_futures_client, mock_repo):
        """测试处理期货响应 - 成功"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=mock_futures_client,
            spot_client=None,
            order_tasks_repo=mock_repo,
        )

        # 模拟找到任务
        mock_repo.find_by_request_id.return_value = {
            "id": 1,
            "type": "order.create",
            "payload": {"symbol": "BTCUSDT"},
        }

        # 模拟响应
        response = {
            "id": "req-123",
            "status": 200,
            "result": {"orderId": 12345},
        }

        # 调用回调
        await handler._handle_futures_response("req-123", response)

        # 验证完成任务
        mock_repo.find_by_request_id.assert_called_once_with("req-123")
        mock_repo.complete.assert_called_once_with(1, {"orderId": 12345})

    @pytest.mark.asyncio
    async def test_handle_futures_response_error(self, mock_futures_client, mock_repo):
        """测试处理期货响应 - 失败"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=mock_futures_client,
            spot_client=None,
            order_tasks_repo=mock_repo,
        )

        # 模拟找到任务
        mock_repo.find_by_request_id.return_value = {
            "id": 1,
            "type": "order.create",
            "payload": {"symbol": "BTCUSDT"},
        }

        # 模拟错误响应
        response = {
            "id": "req-123",
            "status": 400,
            "error": {"msg": "Insufficient balance"},
        }

        # 调用回调
        await handler._handle_futures_response("req-123", response)

        # 验证任务失败
        mock_repo.fail.assert_called_once_with(1, "Insufficient balance")

    @pytest.mark.asyncio
    async def test_handle_futures_response_task_not_found(self, mock_futures_client, mock_repo):
        """测试处理期货响应 - 任务不存在"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=mock_futures_client,
            spot_client=None,
            order_tasks_repo=mock_repo,
        )

        # 模拟未找到任务
        mock_repo.find_by_request_id.return_value = None

        # 调用回调
        await handler._handle_futures_response("unknown-req", {"id": "unknown-req"})

        # 验证未调用任何更新方法
        mock_repo.complete.assert_not_called()
        mock_repo.fail.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_spot_response_success(self, mock_spot_client, mock_repo):
        """测试处理现货响应 - 成功"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=None,
            spot_client=mock_spot_client,
            order_tasks_repo=mock_repo,
        )

        # 模拟找到任务
        mock_repo.find_by_request_id.return_value = {
            "id": 2,
            "type": "order.create",
            "payload": {"symbol": "BTCUSDT"},
        }

        # 模拟响应
        response = {
            "id": "req-456",
            "status": 200,
            "result": {"orderId": 67890},
        }

        # 调用回调
        await handler._handle_spot_response("req-456", response)

        # 验证完成任务
        mock_repo.find_by_request_id.assert_called_once_with("req-456")
        mock_repo.complete.assert_called_once_with(2, {"orderId": 67890})
