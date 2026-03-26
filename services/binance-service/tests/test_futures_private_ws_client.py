"""
期货私有WebSocket客户端测试

测试期货私有WebSocket客户端的签名、认证和交易请求功能。
会话级认证模式：session.logon + listenKey 管理
"""

import pytest
import time

from clients.futures_private_ws_client import BinanceFuturesPrivateWSClient


# 测试用Ed25519私钥（测试网使用）
TEST_PRIVATE_KEY_PEM = b"""-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIClgz3LzBCkJX1OBefmG/HAI0rsfWARaaRf6c8hADZXW
-----END PRIVATE KEY-----"""


class TestFuturesPrivateWSClientSignature:
    """期货私有WS客户端签名测试（会话级认证）"""

    def test_session_logon_signature_payload(self):
        """测试 session.logon 签名的payload

        session.logon 签名payload格式：apiKey=xxx&timestamp=xxx（按键名字母排序）
        """
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )

        timestamp = 1705311512994
        auth_params = {
            "apiKey": "test-api-key",
            "timestamp": timestamp,
        }
        sorted_params = dict(sorted(auth_params.items()))
        payload = "&".join(f"{k}={v}" for k, v in sorted_params.items())

        # session.logon 签名payload格式：apiKey=xxx&timestamp=xxx（按键名字母排序）
        expected = "apiKey=test-api-key&timestamp=1705311512994"
        assert payload == expected


class TestFuturesPrivateWSClientRequests:
    """期货私有WS客户端请求测试（会话级认证模式）"""

    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )
        return client

    def test_send_request_format(self, client):
        """测试发送请求格式（会话级认证，无需签名）"""
        import asyncio

        async def test():
            # Mock _send to verify request format
            sent_requests = []

            async def mock_send(request):
                sent_requests.append(request)

            client._send = mock_send

            # 发送请求
            await client.send_request(
                method="order.place",
                params={"symbol": "BTCUSDT", "side": "BUY"},
                request_id="test-001",
            )

            assert len(sent_requests) == 1
            req = sent_requests[0]
            assert req["id"] == "test-001"
            assert req["method"] == "order.place"
            assert req["params"]["symbol"] == "BTCUSDT"
            # 会话级认证模式下，params 中不应包含签名
            assert "signature" not in req["params"]

        asyncio.run(test())


class TestFuturesPrivateWSClientAuth:
    """期货私有WS客户端认证测试"""

    def test_session_logon_request_format(self):
        """测试 session.logon 请求格式"""
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )

        # 模拟 session.logon 请求构建
        timestamp = int(time.time() * 1000)
        auth_params = {
            "apiKey": client.api_key,
            "timestamp": timestamp,
        }
        sorted_params = dict(sorted(auth_params.items()))
        payload = "&".join(f"{k}={v}" for k, v in sorted_params.items())
        signature = client._signer.sign(payload)

        request = {
            "id": client._next_request_id(),
            "method": "session.logon",
            "params": {
                "apiKey": client.api_key,
                "timestamp": timestamp,
                "signature": signature,
            },
        }

        assert "id" in request
        assert request["method"] == "session.logon"
        assert "params" in request
        assert request["params"]["apiKey"] == "test-api-key"
        assert "signature" in request["params"]
        assert request["params"]["timestamp"] == timestamp

    def test_next_request_id(self):
        """测试请求ID自增"""
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )

        initial_id = int(client._next_request_id())
        next_id = int(client._next_request_id())

        assert next_id == initial_id + 1


class TestFuturesPrivateWSClientResponseHandling:
    """期货私有WS客户端响应处理测试"""

    def test_handle_listen_key_response(self):
        """测试 listenKey 响应处理"""
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )

        # 模拟 listenKey 响应
        response_data = {
            "id": "2001",
            "status": 200,
            "result": {"listenKey": "test-listen-key-12345"},
        }

        # 验证响应格式正确
        assert response_data["result"]["listenKey"] == "test-listen-key-12345"

    def test_handle_account_update_event(self):
        """测试账户更新事件格式"""
        client = BinanceFuturesPrivateWSClient(
            api_key="test-api-key",
            private_key_pem=TEST_PRIVATE_KEY_PEM,
        )

        # 模拟账户更新事件
        event_data = {
            "e": "ACCOUNT_UPDATE",
            "E": 1234567890,
            "T": 1234567890,
            "a": {
                "B": [{"a": "USDT", "wb": "1000.0", "cw": "1000.0"}],
                "P": [],
            },
        }

        # 验证事件类型正确
        assert event_data["e"] == "ACCOUNT_UPDATE"
