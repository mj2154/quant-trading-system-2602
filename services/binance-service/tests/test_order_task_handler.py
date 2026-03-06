"""
订单任务处理器测试

测试 order_tasks 表的订单任务处理逻辑。
"""

import pytest
import uuid
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
        client.send_request = AsyncMock(return_value={"status": 200, "result": {}})
        client.set_response_callback = MagicMock()
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
        client.send_request = AsyncMock(return_value={"status": 200, "result": {}})
        client.set_response_callback = MagicMock()
        return client

    @pytest.fixture
    def mock_repo(self):
        """创建模拟的订单任务仓储"""
        repo = MagicMock()
        repo.set_processing = AsyncMock()
        repo.complete = AsyncMock()
        repo.fail = AsyncMock()
        repo.get_task_by_id = AsyncMock(return_value={"request_id": "test_request_123"})
        repo.find_by_request_id = AsyncMock(return_value={"id": 1})
        return repo

    @pytest.mark.asyncio
    async def test_parse_symbol_with_perp_suffix(self):
        """测试解析期货交易对 (.PERP后缀)"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler()

        # BINANCE:BTCUSDT.PERP → 期货
        symbol, market = handler._parse_symbol("BINANCE:BTCUSDT.PERP")
        assert symbol == "BTCUSDT"
        assert market == "FUTURES"

    @pytest.mark.asyncio
    async def test_parse_symbol_spot(self):
        """测试解析现货交易对（无后缀）"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler()

        # BINANCE:BTCUSDT → 现货
        symbol, market = handler._parse_symbol("BINANCE:BTCUSDT")
        assert symbol == "BTCUSDT"
        assert market == "SPOT"

    @pytest.mark.asyncio
    async def test_parse_symbol_without_prefix(self):
        """测试无前缀的交易对（默认期货）"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler()

        # 无前缀 → 默认期货（向后兼容）
        symbol, market = handler._parse_symbol("BTCUSDT")
        assert symbol == "BTCUSDT"
        assert market == "FUTURES"

    @pytest.mark.asyncio
    async def test_parse_symbol_empty(self):
        """测试空symbol"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler()

        symbol, market = handler._parse_symbol("")
        assert symbol == ""
        assert market == "FUTURES"

    @pytest.mark.asyncio
    async def test_handle_order_create_futures(self, mock_futures_client, mock_repo):
        """测试处理期货订单创建任务（语义化symbol）"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=mock_futures_client,
            spot_client=None,
            order_tasks_repo=mock_repo,
        )

        # 使用语义化symbol格式：BINANCE:BTCUSDT.PERP 表示期货
        # newClientOrderId 是前端生成的 UUID v4 格式（32字符）
        new_client_order_id = uuid.uuid4().hex
        payload = {
            "task_id": 1,
            "type": "order.create",
            "payload": {
                "symbol": "BINANCE:BTCUSDT.PERP",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": 0.001,
                "price": 50000,
                "timeInForce": "GTC",
                "newClientOrderId": new_client_order_id,
            },
        }

        await handler.handle_task(payload)

        # 验证调用 send_request（WS客户端模式）
        mock_futures_client.send_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_order_create_spot(self, mock_spot_client, mock_repo):
        """测试处理现货订单创建任务（语义化symbol）"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=None,
            spot_client=mock_spot_client,
            order_tasks_repo=mock_repo,
        )

        # 使用语义化symbol格式：BINANCE:BTCUSDT 表示现货
        # newClientOrderId 是前端生成的 UUID v4 格式（32字符）
        new_client_order_id = uuid.uuid4().hex
        payload = {
            "task_id": 1,
            "type": "order.create",
            "payload": {
                "symbol": "BINANCE:BTCUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": 0.001,
                "price": 50000,
                "timeInForce": "GTC",
                "newClientOrderId": new_client_order_id,
            },
        }

        await handler.handle_task(payload)

        # 验证调用 send_request（WS客户端模式）
        mock_spot_client.send_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_order_cancel(self, mock_futures_client, mock_repo):
        """测试处理订单取消任务（语义化symbol）"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=mock_futures_client,
            spot_client=None,
            order_tasks_repo=mock_repo,
        )

        # 使用语义化symbol格式
        payload = {
            "task_id": 1,
            "type": "order.cancel",
            "payload": {
                "symbol": "BINANCE:BTCUSDT.PERP",
                "orderId": 12345,
            },
        }

        await handler.handle_task(payload)

        # 验证调用 send_request（WS客户端模式）
        mock_futures_client.send_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_order_query(self, mock_futures_client, mock_repo):
        """测试处理订单查询任务（语义化symbol）"""
        from services.order_task_handler import OrderTaskHandler

        handler = OrderTaskHandler(
            futures_client=mock_futures_client,
            spot_client=None,
            order_tasks_repo=mock_repo,
        )

        # 使用语义化symbol格式
        payload = {
            "task_id": 1,
            "type": "order.query",
            "payload": {
                "symbol": "BINANCE:BTCUSDT.PERP",
                "orderId": 12345,
            },
        }

        await handler.handle_task(payload)

        # 验证调用 send_request（WS客户端模式）
        mock_futures_client.send_request.assert_called_once()

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
