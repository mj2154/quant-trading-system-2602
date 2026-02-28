"""
测试币安期货私有数据HTTP客户端

测试能够正确调用需要签名认证的期货私有API。
"""

import pytest
from unittest.mock import AsyncMock, patch
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


class TestBinanceFuturesPrivateClient:
    """币安期货私有数据客户端测试"""

    def test_client_initialization(self):
        """测试客户端初始化"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        api_key = "test_api_key"
        private_key_pem = generate_test_key()

        client = BinanceFuturesPrivateHTTPClient(
            api_key=api_key,
            private_key_pem=private_key_pem,
        )

        assert client.api_key == api_key
        assert client._signer is not None

    def test_client_base_url(self):
        """测试客户端使用正确的Base URL"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        client = BinanceFuturesPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        assert client.BASE_URL == "https://fapi.binance.com"

    def test_client_with_proxy(self):
        """测试使用代理的客户端初始化"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        client = BinanceFuturesPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
            proxy_url="http://proxy.example.com:8080",
        )

        assert client.api_key == "test_api_key"

    @pytest.mark.asyncio
    async def test_get_account_info_success(self):
        """测试获取期货账户信息成功"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient
        from src.models.futures_account import FuturesAccountInfo

        mock_response = {
            # V3 API 不返回 feeTier, canTrade, canDeposit, canWithdraw, updateTime(顶层)
            "totalInitialMargin": "1000.00",
            "totalMaintMargin": "50.00",
            "totalWalletBalance": "10000.00",
            "totalUnrealizedProfit": "100.00",
            "totalMarginBalance": "10100.00",
            "totalPositionInitialMargin": "100.00",
            "totalOpenOrderInitialMargin": "10.00",
            "totalCrossWalletBalance": "10000.00",
            "totalCrossUnPnl": "100.00",
            "availableBalance": "9900.00",
            "maxWithdrawAmount": "9900.00",
            "assets": [
                {
                    "asset": "USDT",
                    "walletBalance": "10000.00",
                    "unrealizedProfit": "100.00",
                    "marginBalance": "10100.00",
                    "maintMargin": "50.00",
                    "initialMargin": "100.00",
                    "positionInitialMargin": "100.00",
                    "openOrderInitialMargin": "10.00",
                    "crossWalletBalance": "10000.00",
                    "crossUnPnl": "100.00",
                    "availableBalance": "9900.00",
                    "maxWithdrawAmount": "9900.00",
                    "updateTime": 1234567890
                }
            ],
            "positions": [
                {
                    "symbol": "BTCUSDT",
                    "positionSide": "BOTH",
                    "positionAmt": "0.001",
                    "unrealizedProfit": "1.00",
                    "isolatedMargin": "10.00",
                    "notional": "46.00",
                    "isolatedWallet": "10.00",
                    "initialMargin": "10.00",
                    "maintMargin": "1.00",
                    "updateTime": 1234567890
                }
            ],
        }

        client = BinanceFuturesPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        # Mock _signed_request method
        client._signed_request = AsyncMock(return_value=mock_response)

        result = await client.get_account_info()

        # 检查类型名称（避免不同导入路径导致的 isinstance 问题）
        assert result.__class__.__name__ == "FuturesAccountInfo"
        assert result.total_initial_margin == "1000.00"
        assert len(result.positions) == 1
        assert result.positions[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_account_info_includes_signature(self):
        """测试请求包含签名参数"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        client = BinanceFuturesPrivateHTTPClient(
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
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        client = BinanceFuturesPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        # Test _build_signed_params directly
        params = client._build_signed_params({}, recv_window=6000)

        assert params["recvWindow"] == "6000"

    def test_signature_generation(self):
        """测试签名生成逻辑"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        # 生成真实密钥
        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        client = BinanceFuturesPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=private_pem,
        )

        # 验证签名器已初始化
        assert client._signer is not None

        # 测试签名
        payload = "timestamp=1234567890"
        signature = client._signer.sign(payload)
        assert isinstance(signature, str)


class TestFuturesSignedRequestHelper:
    """期货签名请求辅助方法测试"""

    def test_build_signed_params(self):
        """测试构建签名URL参数"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        client = BinanceFuturesPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        # Mock time to get deterministic timestamp
        with patch('src.clients.futures_private_http_client.time.time', return_value=1234567.89):
            params = {"symbol": "BTCUSDT"}
            result = client._build_signed_params(params)

        assert "symbol" in result
        assert "timestamp" in result
        assert "signature" in result
        assert result["symbol"] == "BTCUSDT"

    def test_build_signed_params_with_recv_window(self):
        """测试构建带recvWindow的签名参数"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        client = BinanceFuturesPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        with patch('src.clients.futures_private_http_client.time.time', return_value=1234567.89):
            result = client._build_signed_params({"symbol": "BTCUSDT"}, recv_window=10000)

        assert "recvWindow" in result
        assert result["recvWindow"] == "10000"

    def test_timestamp_generation(self):
        """测试时间戳生成"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        client = BinanceFuturesPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        timestamp = client._generate_timestamp()
        assert isinstance(timestamp, str)
        assert len(timestamp) == 13  # 毫秒时间戳


class TestFuturesAccountModel:
    """期货账户模型测试"""

    def test_futures_account_info_parsing(self):
        """测试期货账户信息解析 (V3 API)"""
        from src.models.futures_account import FuturesAccountInfo, FuturesPosition

        mock_data = {
            # V3 API 不返回 feeTier, canTrade, canDeposit, canWithdraw, updateTime(顶层)
            "totalInitialMargin": "1000.00",
            "totalMaintMargin": "50.00",
            "totalWalletBalance": "10000.00",
            "totalUnrealizedProfit": "100.00",
            "totalMarginBalance": "10100.00",
            "totalPositionInitialMargin": "100.00",
            "totalOpenOrderInitialMargin": "10.00",
            "totalCrossWalletBalance": "10000.00",
            "totalCrossUnPnl": "100.00",
            "availableBalance": "9900.00",
            "maxWithdrawAmount": "9900.00",
            "assets": [
                {
                    "asset": "USDT",
                    "walletBalance": "10000.00",
                    "unrealizedProfit": "100.00",
                    "marginBalance": "10100.00",
                    "maintMargin": "50.00",
                    "initialMargin": "100.00",
                    "positionInitialMargin": "100.00",
                    "openOrderInitialMargin": "10.00",
                    "crossWalletBalance": "10000.00",
                    "crossUnPnl": "100.00",
                    "availableBalance": "9900.00",
                    "maxWithdrawAmount": "9900.00",
                    "updateTime": 1234567890
                }
            ],
            "positions": [
                {
                    "symbol": "BTCUSDT",
                    "positionSide": "BOTH",
                    "positionAmt": "0.001",
                    "unrealizedProfit": "1.00",
                    "isolatedMargin": "10.00",
                    "notional": "46.00",
                    "isolatedWallet": "10.00",
                    "initialMargin": "10.00",
                    "maintMargin": "1.00",
                    "updateTime": 1234567890
                }
            ],
        }

        account = FuturesAccountInfo.model_validate(mock_data)

        assert account.total_initial_margin == "1000.00"
        assert account.available_balance == "9900.00"
        assert len(account.assets) == 1
        assert account.assets[0].asset == "USDT"
        assert len(account.positions) == 1
        assert account.positions[0].symbol == "BTCUSDT"

    def test_futures_position_parsing(self):
        """测试期货持仓信息解析"""
        from src.models.futures_account import FuturesPosition

        mock_data = {
            "symbol": "ETHUSDT",
            "positionSide": "LONG",
            "positionAmt": "0.5",
            "entryPrice": "3000.00",
            "markPrice": "3100.00",
            "unrealizedProfit": "50.00",
            "liquidationPrice": "2500.00",
            "marginSize": "15.00",
        }

        position = FuturesPosition.model_validate(mock_data)

        assert position.symbol == "ETHUSDT"
        assert position.position_side == "LONG"
        assert position.position_amt == "0.5"


class TestFuturesAdditionalEndpoints:
    """期货额外端点测试"""

    @pytest.mark.asyncio
    async def test_get_balance(self):
        """测试获取期货账户余额"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        mock_response = [
            {
                "accountAlias": "SXXX",
                "asset": "USDT",
                "balance": "10000.00",
                "crossWalletBalance": "10000.00",
                "crossUnrealizedProfit": "0.00",
                "availableBalance": "10000.00",
                "maxWithdrawAmount": "10000.00",
            },
            {
                "accountAlias": "SXXX",
                "asset": "BTC",
                "balance": "0.001",
                "crossWalletBalance": "0.001",
                "crossUnrealizedProfit": "0.00",
                "availableBalance": "0.001",
                "maxWithdrawAmount": "0.001",
            },
        ]

        client = BinanceFuturesPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        client._signed_request = AsyncMock(return_value=mock_response)

        result = await client.get_balance()

        assert len(result) == 2
        assert result[0]["asset"] == "USDT"
        assert result[0]["balance"] == "10000.00"

    @pytest.mark.asyncio
    async def test_get_position_risk(self):
        """测试获取持仓风险"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        mock_response = [
            {
                "symbol": "BTCUSDT",
                "positionSide": "BOTH",
                "positionAmt": "0.001",
                "entryPrice": "45000.00",
                "markPrice": "46000.00",
                "unrealizedProfit": "1.00",
                "liquidationPrice": "40000.00",
                "riskRate": "0.5",
            }
        ]

        client = BinanceFuturesPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        client._signed_request = AsyncMock(return_value=mock_response)

        result = await client.get_position_risk()

        assert len(result) == 1
        assert result[0]["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_payload_creation(self):
        """测试payload创建"""
        from src.clients.futures_private_http_client import BinanceFuturesPrivateHTTPClient

        client = BinanceFuturesPrivateHTTPClient(
            api_key="test_api_key",
            private_key_pem=generate_test_key(),
        )

        params = {
            "symbol": "BTCUSDT",
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
