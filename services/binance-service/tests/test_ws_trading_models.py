"""
WebSocket交易模型测试

测试WebSocket请求/响应模型的行为。
"""

import pytest
from pydantic import ValidationError

from models.ws_trading_models import (
    WSRequest,
    WSResponse,
    WSAuthParams,
    WSOrderParams,
    WSOrderResponse,
)


class TestWSRequest:
    """WebSocket请求模型测试"""

    def test_create_basic_request(self):
        """测试创建基础请求"""
        request = WSRequest(
            id="test-id-123",
            method="order.place",
            params={"symbol": "BTCUSDT"},
        )
        assert request.id == "test-id-123"
        assert request.method == "order.place"
        assert request.params["symbol"] == "BTCUSDT"

    def test_request_without_params(self):
        """测试无参数的请求"""
        request = WSRequest(
            id="test-id-456",
            method="session.status",
        )
        assert request.id == "test-id-456"
        assert request.method == "session.status"
        assert request.params is None


class TestWSResponse:
    """WebSocket响应模型测试"""

    def test_successful_response(self):
        """测试成功响应"""
        response = WSResponse(
            id="test-id-123",
            status=200,
            result={"orderId": "12345", "symbol": "BTCUSDT"},
        )
        assert response.id == "test-id-123"
        assert response.status == 200
        assert response.result is not None
        assert response.error is None

    def test_error_response(self):
        """测试错误响应"""
        response = WSResponse(
            id="test-id-456",
            status=400,
            error={"code": -1102, "msg": "Mandatory parameter missing"},
        )
        assert response.id == "test-id-456"
        assert response.status == 400
        assert response.result is None
        assert response.error is not None
        assert response.error["code"] == -1102


class TestWSAuthParams:
    """认证参数模型测试"""

    def test_create_auth_params(self):
        """测试创建认证参数"""
        params = WSAuthParams(
            api_key="test-api-key",
            signature="test-signature",
            timestamp=1705311512994,
        )
        assert params.api_key == "test-api-key"
        assert params.signature == "test-signature"
        assert params.timestamp == 1705311512994

    def test_auth_params_with_recv_window(self):
        """测试带recvWindow的认证参数"""
        params = WSAuthParams(
            api_key="test-api-key",
            signature="test-signature",
            timestamp=1705311512994,
            recv_window=5000,
        )
        assert params.recv_window == 5000


class TestWSOrderParams:
    """订单参数模型测试"""

    def test_limit_order_params(self):
        """测试限价单参数"""
        params = WSOrderParams(
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            time_in_force="GTC",
            price="42000.00",
            quantity="0.001",
            timestamp=1705311512994,
            api_key="test-api-key",
            signature="test-signature",
        )
        assert params.symbol == "BTCUSDT"
        assert params.side == "BUY"
        assert params.order_type == "LIMIT"
        assert params.time_in_force == "GTC"
        assert params.price == "42000.00"
        assert params.quantity == "0.001"

    def test_market_order_params(self):
        """测试市价单参数"""
        params = WSOrderParams(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity="0.001",
            timestamp=1705311512994,
            api_key="test-api-key",
            signature="test-signature",
        )
        assert params.order_type == "MARKET"
        assert params.price is None
        assert params.time_in_force is None

    def test_order_with_client_order_id(self):
        """测试带客户端订单ID的订单"""
        params = WSOrderParams(
            symbol="BTCUSDT",
            side="SELL",
            order_type="LIMIT",
            quantity="0.01",
            price="43000.00",
            time_in_force="GTC",
            timestamp=1705311512994,
            api_key="test-api-key",
            signature="test-signature",
            new_client_order_id="my-order-123",
        )
        assert params.new_client_order_id == "my-order-123"


class TestWSOrderResponse:
    """订单响应模型测试"""

    def test_order_response_parsing(self):
        """测试订单响应解析"""
        response_data = {
            "orderId": "336829446",
            "symbol": "BTCUSDT",
            "status": "NEW",
            "clientOrderId": "FqEw6cn0vDhrkmfiwLYPeo",
            "price": "42088.00",
            "origQty": "0.100",
            "executedQty": "0.000",
        }
        response = WSOrderResponse.model_validate(response_data)
        assert response.order_id == "336829446"
        assert response.symbol == "BTCUSDT"
        assert response.status == "NEW"
        assert response.client_order_id == "FqEw6cn0vDhrkmfiwLYPeo"
