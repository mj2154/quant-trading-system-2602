"""
测试币安现货私有数据HTTP客户端

测试能够正确调用需要签名认证的私有API。
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def generate_test_key():
    """生成测试用Ed25519密钥对"""
    private_key = ed25519.Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return private_pem


class TestBinanceSpotPrivateClient:
    """币安现货私有数据客户端测试"""

    def test_client_initialization(self):
        """测试客户端初始化"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        api_key = "test_api_key"
        private_key_pem = generate_test_key()

        client = BinanceSpotPrivateHTTPClient(
            api_key=api_key,
            private_key_pem=private_key_pem,
        )

        assert client.api_key == api_key
        assert client._signer is not None

    def test_client_with_proxy(self):
        """测试使用代理的客户端初始化"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
            proxy_url="http://proxy.example.com:8080",
        )

        assert client.api_key == "test_api_key"

    @pytest.mark.asyncio
    async def test_get_account_info_success(self):
        """测试获取账户信息成功"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient
        from src.models.spot_account import SpotAccountInfo

        mock_response = {
            "accountType": "SPOT",
            "balances": [
                {"asset": "BTC", "free": "1.00000000", "locked": "0.50000000"},
                {"asset": "USDT", "free": "1000.00000000", "locked": "0.00000000"},
            ],
            "canTrade": True,
            "canWithdraw": True,
            "canDeposit": True,
            "updateTime": 1234567890,
        }

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        # Mock _signed_request method
        client._signed_request = AsyncMock(return_value=mock_response)

        result = await client.get_account_info()

        assert isinstance(result, SpotAccountInfo)
        assert result.account_type == "SPOT"
        assert len(result.balances) == 2
        assert result.can_trade is True

    @pytest.mark.asyncio
    async def test_get_account_info_includes_signature(self):
        """测试请求包含签名参数"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        # Test _build_signed_params directly to verify signature params
        params = client._build_signed_params({}, recv_window=5000)

        assert "timestamp" in params
        assert "signature" in params
        # Verify timestamp is a 13-digit number
        assert len(params["timestamp"]) == 13
        assert params["recvWindow"] == "5000"

    @pytest.mark.asyncio
    async def test_get_account_info_with_recv_window(self):
        """测试带recvWindow参数的请求"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        # Test _build_signed_params directly
        params = client._build_signed_params({}, recv_window=6000)

        assert params["recvWindow"] == "6000"

    def test_signature_generation(self):
        """测试签名生成逻辑"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization

        # 生成真实密钥
        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=private_pem,
        )

        # 验证签名器已初始化
        assert client._signer is not None

        # 测试签名
        payload = "timestamp=1234567890"
        signature = client._signer.sign(payload)
        assert isinstance(signature, str)


class TestSignedRequestHelper:
    """签名请求辅助方法测试"""

    def test_build_signed_params(self):
        """测试构建签名URL参数"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        # Mock time to get deterministic timestamp
        with patch('src.clients.spot_private_http_client.time.time', return_value=1234567.89):
            params = {"symbol": "BNBUSDT"}
            result = client._build_signed_params(params)

        assert "symbol" in result
        assert "timestamp" in result
        assert "signature" in result
        assert result["symbol"] == "BNBUSDT"

    def test_build_signed_params_with_recv_window(self):
        """测试构建带recvWindow的签名参数"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        with patch('src.clients.spot_private_http_client.time.time', return_value=1234567.89):
            result = client._build_signed_params({"symbol": "BTCUSDT"}, recv_window=10000)

        assert "recvWindow" in result
        assert result["recvWindow"] == "10000"

    def test_timestamp_generation(self):
        """测试时间戳生成"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        timestamp = client._generate_timestamp()
        assert isinstance(timestamp, str)
        assert len(timestamp) == 13  # 毫秒时间戳

    def test_payload_creation(self):
        """测试payload创建"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        params = {
            "symbol": "BNBUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": "1",
            "price": "50000",
            "timestamp": "1234567890",
            "recvWindow": "5000",
        }

        payload = client._create_payload(params)
        assert "quantity=1" in payload
        assert "price=50000" in payload
        assert "recvWindow=5000" in payload
        assert "side=BUY" in payload
        assert "symbol=BNBUSDT" in payload
        assert "timestamp=1234567890" in payload
        # 验证按key排序
        keys_order = ["price", "quantity", "recvWindow", "side", "symbol", "timestamp"]
        current_pos = 0
        for key in keys_order:
            key_pos = payload.index(f"{key}=")
            assert key_pos >= current_pos
            current_pos = key_pos


class TestPrivateClientMethods:
    """私有客户端其他方法测试"""

    @pytest.mark.asyncio
    async def test_get_order(self):
        """测试获取订单信息"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        mock_response = {
            "symbol": "BNBUSDT",
            "orderId": "123456",
            "status": "FILLED",
        }

        client._signed_request = AsyncMock(return_value=mock_response)

        result = await client.get_order(symbol="BNBUSDT", order_id="123456")

        assert result["symbol"] == "BNBUSDT"
        assert result["orderId"] == "123456"

    @pytest.mark.asyncio
    async def test_get_order_with_client_order_id(self):
        """测试使用客户端订单ID获取订单"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        mock_response = {
            "symbol": "BNBUSDT",
            "clientOrderId": "my_order_id",
            "status": "FILLED",
        }

        client._signed_request = AsyncMock(return_value=mock_response)

        result = await client.get_order(
            symbol="BNBUSDT",
            orig_client_order_id="my_order_id"
        )

        assert result["clientOrderId"] == "my_order_id"

    @pytest.mark.asyncio
    async def test_get_open_orders(self):
        """测试获取当前挂单"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        mock_response = [
            {"symbol": "BNBUSDT", "orderId": "123"},
            {"symbol": "ETHUSDT", "orderId": "456"},
        ]

        client._signed_request = AsyncMock(return_value=mock_response)

        result = await client.get_open_orders()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_open_orders_with_symbol(self):
        """测试获取指定交易对的挂单"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        mock_response = [{"symbol": "BNBUSDT", "orderId": "123"}]

        client._signed_request = AsyncMock(return_value=mock_response)

        result = await client.get_open_orders(symbol="BNBUSDT")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_all_orders(self):
        """测试获取所有订单"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        mock_response = [
            {"symbol": "BNBUSDT", "orderId": "123"},
            {"symbol": "BNBUSDT", "orderId": "456"},
        ]

        client._signed_request = AsyncMock(return_value=mock_response)

        result = await client.get_all_orders(symbol="BNBUSDT", limit=100)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_all_orders_with_time_range(self):
        """测试带时间范围获取订单"""
        from src.clients.spot_private_http_client import BinanceSpotPrivateHTTPClient

        client = BinanceSpotPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        mock_response = [{"symbol": "BNBUSDT", "orderId": "123"}]

        client._signed_request = AsyncMock(return_value=mock_response)

        result = await client.get_all_orders(
            symbol="BNBUSDT",
            start_time=1700000000000,
            end_time=1700100000000,
        )

        assert len(result) == 1
