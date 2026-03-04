"""
期货私有WebSocket客户端测试

测试期货私有WebSocket客户端的签名、认证和交易请求功能。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import time

from clients.futures_private_ws_client import BinanceFuturesPrivateWSClient
from models.ws_trading_models import WSResponse


# 测试用Ed25519私钥（测试网使用）
TEST_PRIVATE_KEY_PEM = b"""-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIClgz3LzBCkJX1OBefmG/HAI0rsfWARaaRf6c8hADZXW
-----END PRIVATE KEY-----"""


class TestFuturesPrivateWSClientSignature:
    """期货私有WS客户端签名测试"""

    def test_create_signed_payload_alphabetical_order(self):
        """测试签名payload按字母顺序排序"""
        # 创建客户端实例
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )

        # 测试签名payload生成 - WebSocket需要按键名字母顺序排序
        params = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": "0.001",
            "price": "42000.00",
            "timeInForce": "GTC",
            "timestamp": 1705311512994,
        }

        payload = client._create_ws_payload(params)

        # WebSocket签名payload必须按键名字母顺序排序
        expected = (
            "price=42000.00&quantity=0.001&side=BUY&"
            "symbol=BTCUSDT&timeInForce=GTC&timestamp=1705311512994&type=LIMIT"
        )
        assert payload == expected

    def test_auth_signature_payload(self):
        """测试认证签名的payload"""
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )

        timestamp = 1705311512994
        payload = client._create_auth_payload(timestamp)

        # 认证签名payload格式：timestamp=xxx
        expected = "timestamp=1705311512994"
        assert payload == expected


class TestFuturesPrivateWSClientRequests:
    """期货私有WS客户端请求测试"""

    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )
        return client

    def test_build_order_params(self, client):
        """测试构建订单参数"""
        params = client._build_order_params(
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            quantity=0.001,
            price=42000.00,
            time_in_force="GTC",
        )

        assert params["symbol"] == "BTCUSDT"
        assert params["side"] == "BUY"
        assert params["type"] == "LIMIT"
        assert params["quantity"] == "0.001"
        assert params["price"] == "42000.0"
        assert params["timeInForce"] == "GTC"
        assert "timestamp" in params
        assert "signature" in params

    def test_build_cancel_order_params(self, client):
        """测试构建撤单参数"""
        params = client._build_cancel_order_params(
            symbol="BTCUSDT",
            order_id="12345",
        )

        assert params["symbol"] == "BTCUSDT"
        assert params["orderId"] == "12345"
        assert "timestamp" in params
        assert "signature" in params

    def test_build_query_order_params(self, client):
        """测试构建查询订单参数"""
        params = client._build_query_order_params(
            symbol="BTCUSDT",
            order_id="12345",
        )

        assert params["symbol"] == "BTCUSDT"
        assert params["orderId"] == "12345"
        assert "timestamp" in params
        assert "signature" in params


class TestFuturesPrivateWSClientAuth:
    """期货私有WS客户端认证测试"""

    def test_authentication_request_format(self):
        """测试认证请求格式"""
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )

        # 模拟认证
        timestamp = int(time.time() * 1000)
        request = client._create_auth_request(timestamp)

        assert "id" in request
        assert request["method"] == "session.logon"
        assert "params" in request
        assert request["params"]["apiKey"] == "test-api-key"
        assert "signature" in request["params"]
        assert request["params"]["timestamp"] == timestamp


class TestFuturesPrivateWSClientResponseHandling:
    """期货私有WS客户端响应处理测试"""

    def test_parse_response_success(self):
        """测试解析成功响应"""
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )

        response_data = {
            "id": "test-id",
            "status": 200,
            "result": {"orderId": "12345", "symbol": "BTCUSDT"},
        }

        response = client._parse_response(response_data)
        assert isinstance(response, WSResponse)
        assert response.status == 200
        assert response.result is not None
        assert response.result["orderId"] == "12345"

    def test_parse_response_error(self):
        """测试解析错误响应"""
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )

        response_data = {
            "id": "test-id",
            "status": 400,
            "error": {"code": -1102, "msg": "Missing parameter"},
        }

        response = client._parse_response(response_data)
        assert isinstance(response, WSResponse)
        assert response.status == 400
        assert response.error is not None
        assert response.error["code"] == -1102
