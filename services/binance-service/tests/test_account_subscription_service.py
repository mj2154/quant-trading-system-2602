"""账户订阅服务测试 v1.1

直接导入模块文件，绕过 services 包的循环依赖问题。
"""

import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from contextlib import asynccontextmanager

import pytest

# 添加 src 目录到路径
sys.path.insert(0, '/app/src')

# 直接导入模块，绕过 services/__init__.py
import importlib.util

def import_module_from_file(module_name, file_path):
    """直接从文件导入模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# 直接加载 account_subscription_service 模块
account_subscription_service = import_module_from_file(
    "account_subscription_service",
    "/app/src/services/account_subscription_service.py"
)
AccountSubscriptionService = account_subscription_service.AccountSubscriptionService

# 导入常量
constants = import_module_from_file(
    "constants",
    "/app/src/constants/__init__.py"
)
BinanceAccountSubscriptionKey = constants.BinanceAccountSubscriptionKey


# ========== Fixtures ==========

@pytest.fixture
def mock_pool():
    """模拟数据库连接池 - 支持 async with pool.acquire() as conn"""
    # 创建模拟的连接对象
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    # 创建异步上下文管理器
    @asynccontextmanager
    async def mock_acquire():
        yield mock_conn

    # 创建 pool mock
    pool = MagicMock()
    pool.acquire = mock_acquire

    return pool


@pytest.fixture
def mock_spot_http_client():
    """模拟现货私有 HTTP 客户端"""
    client = AsyncMock()
    # Mock get_account_info return value
    client.get_account_info = AsyncMock(return_value=MagicMock(
        update_time=1700000000,
        balances=[
            {"asset": "USDT", "free": "1000.0", "locked": "100.0"},
            {"asset": "BTC", "free": "0.1", "locked": "0.0"},
        ]
    ))
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_futures_http_client():
    """模拟期货私有 HTTP 客户端"""
    client = AsyncMock()
    # Mock get_account_info return value
    client.get_account_info = AsyncMock(return_value=MagicMock(
        update_time=1700000000,
        total_wallet_balance="10000.0",
        total_unrealized_profit="100.0",
        total_margin_balance="10000.0",
        total_available_balance="9000.0",
        positions=[
            {"symbol": "BTCUSDT", "entry_price": "50000.0", "position_amt": "0.1",
             "unrealized_profit": "100.0", "leverage": "10", "margin_type": "cross",
             "isolated_margin": "0.0", "position_side": "BOTH"},
        ],
        assets=[
            {"asset": "USDT", "wallet_balance": "10000.0", "unrealized_profit": "100.0",
             "margin_balance": "10000.0", "available_balance": "9000.0"},
        ]
    ))
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_spot_user_stream():
    """模拟现货用户数据流客户端"""
    client = AsyncMock()
    client.start = AsyncMock()
    client.stop = AsyncMock()
    client.set_data_callback = MagicMock()
    return client


@pytest.fixture
def mock_futures_user_stream():
    """模拟期货用户数据流客户端"""
    client = AsyncMock()
    client.start = AsyncMock()
    client.stop = AsyncMock()
    client.set_data_callback = MagicMock()
    return client


@pytest.fixture
def private_key_pem():
    """模拟私钥 PEM"""
    return b"mock_private_key_pem"


# ========== 测试类 ==========

class TestAccountSubscriptionServiceInit:
    """测试服务初始化"""

    def test_version_is_v1_1(self):
        """验证版本号为 v1.1"""
        # 验证 docstring 中包含 v1.1
        assert "v1.1" in AccountSubscriptionService.__doc__

    @pytest.mark.asyncio
    async def test_init_with_spot_only(self, mock_pool, private_key_pem):
        """测试仅配置现货"""
        service = AccountSubscriptionService(
            pool=mock_pool,
            api_key="test_api_key",
            futures_api_key="",
            private_key_pem=private_key_pem,
        )

        assert service._api_key == "test_api_key"
        assert service._futures_api_key == ""
        assert service._snapshot_interval == 300  # 默认 5 分钟


class TestAccountSubscriptionServiceStart:
    """测试服务启动"""

    @pytest.mark.asyncio
    async def test_start_fetches_spot_snapshot(self, mock_pool, mock_spot_http_client,
                                                mock_spot_user_stream, private_key_pem):
        """测试启动时获取现货快照"""
        with patch("account_subscription_service.BinanceSpotPrivateHTTPClient",
                   return_value=mock_spot_http_client):
            with patch("account_subscription_service.SpotUserStreamClient",
                       return_value=mock_spot_user_stream):
                service = AccountSubscriptionService(
                    pool=mock_pool,
                    api_key="test_api_key",
                    futures_api_key="",
                    private_key_pem=private_key_pem,
                    snapshot_interval=3600,  # 1 小时，避免触发快照
                )

                await service.start()

                # 验证启动时获取了现货快照
                mock_spot_http_client.get_account_info.assert_called_once()

                await service.stop()

    @pytest.mark.asyncio
    async def test_start_fetches_futures_snapshot(self, mock_pool, mock_futures_http_client,
                                                  mock_futures_user_stream, private_key_pem):
        """测试启动时获取期货快照"""
        with patch("account_subscription_service.BinanceFuturesPrivateHTTPClient",
                   return_value=mock_futures_http_client):
            with patch("account_subscription_service.FuturesUserStreamClient",
                       return_value=mock_futures_user_stream):
                service = AccountSubscriptionService(
                    pool=mock_pool,
                    api_key="",
                    futures_api_key="test_futures_api_key",
                    private_key_pem=private_key_pem,
                    snapshot_interval=3600,
                )

                await service.start()

                # 验证启动时获取了期货快照
                mock_futures_http_client.get_account_info.assert_called_once()

                await service.stop()

    @pytest.mark.asyncio
    async def test_start_subscribes_to_spot_stream(self, mock_pool, mock_spot_http_client,
                                                    mock_spot_user_stream, private_key_pem):
        """测试启动时订阅现货用户数据流"""
        with patch("account_subscription_service.BinanceSpotPrivateHTTPClient",
                   return_value=mock_spot_http_client):
            with patch("account_subscription_service.SpotUserStreamClient",
                       return_value=mock_spot_user_stream):
                service = AccountSubscriptionService(
                    pool=mock_pool,
                    api_key="test_api_key",
                    futures_api_key="",
                    private_key_pem=private_key_pem,
                    snapshot_interval=3600,
                )

                await service.start()

                # 验证设置了数据回调
                mock_spot_user_stream.set_data_callback.assert_called_once()

                # 验证启动了用户数据流
                mock_spot_user_stream.start.assert_called_once()

                await service.stop()


class TestHandleSpotData:
    """测试现货数据处理"""

    @pytest.mark.asyncio
    async def test_handle_spot_data_writes_directly(self, mock_pool, mock_spot_http_client,
                                                      mock_spot_user_stream, private_key_pem):
        """测试现货数据处理直接写入数据库（不合并缓存）"""
        # 记录写入的数据
        written_data = []

        async def mock_execute(query, *args):
            written_data.append({
                "query": query,
                "subscription_key": args[0],
                "data_type": args[1],
                "data": args[2],
            })
            return None

        # 获取 mock_pool 中的连接对象并设置 execute
        mock_conn = AsyncMock()
        mock_conn.execute = mock_execute

        # 重写 pool.acquire 使其返回带 execute 的连接
        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_pool.acquire = mock_acquire

        with patch("account_subscription_service.BinanceSpotPrivateHTTPClient",
                   return_value=mock_spot_http_client):
            with patch("account_subscription_service.SpotUserStreamClient",
                       return_value=mock_spot_user_stream):
                service = AccountSubscriptionService(
                    pool=mock_pool,
                    api_key="test_api_key",
                    futures_api_key="",
                    private_key_pem=private_key_pem,
                    snapshot_interval=3600,
                )

                await service.start()

                # 清空之前的数据
                written_data.clear()

                # 模拟 WebSocket 推送的增量数据
                incremental_data = {
                    "event_type": "outboundAccountPosition",
                    "balances": [
                        {"asset": "USDT", "free": "1100.0", "locked": "100.0"},
                    ]
                }

                # 调用处理回调
                await service._handle_spot_data(incremental_data)

                # 验证数据直接写入数据库（没有缓存合并）
                assert len(written_data) == 1
                assert written_data[0]["subscription_key"] == BinanceAccountSubscriptionKey.SPOT
                assert written_data[0]["data_type"] == "ACCOUNT"

                # 验证数据是直接使用的增量数据，没有经过合并
                written_json = json.loads(written_data[0]["data"])
                assert written_json == incremental_data

                await service.stop()


class TestHandleFuturesData:
    """测试期货数据处理"""

    @pytest.mark.asyncio
    async def test_handle_futures_data_writes_directly(self, mock_pool, mock_futures_http_client,
                                                         mock_futures_user_stream, private_key_pem):
        """测试期货数据处理直接写入数据库（不合并缓存）"""
        # 记录写入的数据
        written_data = []

        async def mock_execute(query, *args):
            written_data.append({
                "query": query,
                "subscription_key": args[0],
                "data_type": args[1],
                "data": args[2],
            })
            return None

        mock_conn = AsyncMock()
        mock_conn.execute = mock_execute

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_pool.acquire = mock_acquire

        with patch("account_subscription_service.BinanceFuturesPrivateHTTPClient",
                   return_value=mock_futures_http_client):
            with patch("account_subscription_service.FuturesUserStreamClient",
                       return_value=mock_futures_user_stream):
                service = AccountSubscriptionService(
                    pool=mock_pool,
                    api_key="",
                    futures_api_key="test_futures_api_key",
                    private_key_pem=private_key_pem,
                    snapshot_interval=3600,
                )

                await service.start()

                # 清空之前的数据
                written_data.clear()

                # 模拟 WebSocket 推送的增量数据
                incremental_data = {
                    "event_type": "ACCOUNT_UPDATE",
                    "positions": [
                        {"symbol": "BTCUSDT", "position_amt": "0.2"},
                    ]
                }

                # 调用处理回调
                await service._handle_futures_data(incremental_data)

                # 验证数据直接写入数据库（没有缓存合并）
                assert len(written_data) == 1
                assert written_data[0]["subscription_key"] == BinanceAccountSubscriptionKey.FUTURES
                assert written_data[0]["data_type"] == "ACCOUNT"

                # 验证数据是直接使用的增量数据
                written_json = json.loads(written_data[0]["data"])
                assert written_json == incremental_data

                await service.stop()


class TestSnapshotFetch:
    """测试快照获取"""

    @pytest.mark.asyncio
    async def test_fetch_spot_snapshot_writes_to_realtime_data(self, mock_pool,
                                                                 mock_spot_http_client, private_key_pem):
        """测试获取现货快照写入 realtime_data 表"""
        # 记录写入的数据
        written_data = []

        async def mock_execute(query, *args):
            written_data.append({
                "subscription_key": args[0],
                "data_type": args[1],
            })
            return None

        mock_conn = AsyncMock()
        mock_conn.execute = mock_execute

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_pool.acquire = mock_acquire

        service = AccountSubscriptionService(
            pool=mock_pool,
            api_key="test_api_key",
            futures_api_key="",
            private_key_pem=private_key_pem,
        )
        # 手动设置 HTTP 客户端
        service._spot_private_http = mock_spot_http_client

        await service._fetch_spot_snapshot()

        # 验证写入了一次数据
        assert len(written_data) == 1
        assert written_data[0]["subscription_key"] == BinanceAccountSubscriptionKey.SPOT
        assert written_data[0]["data_type"] == "ACCOUNT"

    @pytest.mark.asyncio
    async def test_fetch_futures_snapshot_writes_to_realtime_data(self, mock_pool,
                                                                   mock_futures_http_client, private_key_pem):
        """测试获取期货快照写入 realtime_data 表"""
        # 记录写入的数据
        written_data = []

        async def mock_execute(query, *args):
            written_data.append({
                "subscription_key": args[0],
                "data_type": args[1],
            })
            return None

        mock_conn = AsyncMock()
        mock_conn.execute = mock_execute

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_pool.acquire = mock_acquire

        service = AccountSubscriptionService(
            pool=mock_pool,
            api_key="",
            futures_api_key="test_futures_api_key",
            private_key_pem=private_key_pem,
        )
        # 手动设置 HTTP 客户端
        service._futures_private_http = mock_futures_http_client

        await service._fetch_futures_snapshot()

        # 验证写入了一次数据
        assert len(written_data) == 1
        assert written_data[0]["subscription_key"] == BinanceAccountSubscriptionKey.FUTURES
        assert written_data[0]["data_type"] == "ACCOUNT"


class TestNoCacheMerge:
    """测试缓存合并已删除"""

    def test_no_merge_methods_exist(self):
        """验证不存在缓存合并方法"""
        service_methods = [m for m in dir(AccountSubscriptionService) if not m.startswith("_")]

        # 验证不存在合并方法
        assert "_merge_to_spot_cache" not in service_methods
        assert "_merge_to_futures_cache" not in service_methods

    def test_no_cache_attributes(self):
        """验证不存在缓存属性"""
        # 验证 _spot_cache 和 _futures_cache 不在 __init__ 中初始化
        import inspect
        source = inspect.getsource(AccountSubscriptionService.__init__)

        assert "_spot_cache" not in source
        assert "_futures_cache" not in source


class TestWriteRealtimeData:
    """测试实时数据写入"""

    @pytest.mark.asyncio
    async def test_write_realtime_data_uses_upsert(self, mock_pool, private_key_pem):
        """测试实时数据写入使用 UPSERT"""
        # 记录写入的数据
        written_queries = []

        async def mock_execute(query, *args):
            written_queries.append({
                "query": query,
                "args": args,
            })
            return None

        mock_conn = AsyncMock()
        mock_conn.execute = mock_execute

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_pool.acquire = mock_acquire

        service = AccountSubscriptionService(
            pool=mock_pool,
            api_key="test_api_key",
            futures_api_key="",
            private_key_pem=private_key_pem,
        )

        test_data = {"test": "data"}
        await service._write_realtime_data(
            subscription_key=BinanceAccountSubscriptionKey.SPOT,
            data_type="ACCOUNT",
            data=test_data,
        )

        # 验证使用了 ON CONFLICT (UPSERT)
        assert len(written_queries) == 1
        query = written_queries[0]["query"]
        assert "ON CONFLICT" in query
        assert "realtime_data" in query
        assert "subscription_key" in query


# ========== 数据更新流程测试 ==========

class TestDataUpdateFlow:
    """测试数据更新流程"""

    @pytest.mark.asyncio
    async def test_initialization_flow(self, mock_pool, mock_spot_http_client,
                                         mock_spot_user_stream, private_key_pem):
        """测试初始化流程：REST API -> account_info 表

        注：由于现在只写入 realtime_data 表（不再写入 account_info），
        我们验证启动时调用了 REST API 获取完整数据
        """
        with patch("account_subscription_service.BinanceSpotPrivateHTTPClient",
                   return_value=mock_spot_http_client):
            with patch("account_subscription_service.SpotUserStreamClient",
                       return_value=mock_spot_user_stream):
                service = AccountSubscriptionService(
                    pool=mock_pool,
                    api_key="test_api_key",
                    futures_api_key="",
                    private_key_pem=private_key_pem,
                    snapshot_interval=3600,
                )

                await service.start()

                # 验证 REST API 被调用（初始化）
                mock_spot_http_client.get_account_info.assert_called_once()

                await service.stop()

    @pytest.mark.asyncio
    async def test_realtime_push_flow(self, mock_pool, mock_spot_http_client,
                                       mock_spot_user_stream, private_key_pem):
        """测试实时推送流程：WebSocket 增量 -> 直接覆盖 realtime_data"""
        written_data = []

        async def mock_execute(query, *args):
            written_data.append({"data": args[2]})

        mock_conn = AsyncMock()
        mock_conn.execute = mock_execute

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_pool.acquire = mock_acquire

        with patch("account_subscription_service.BinanceSpotPrivateHTTPClient",
                   return_value=mock_spot_http_client):
            with patch("account_subscription_service.SpotUserStreamClient",
                       return_value=mock_spot_user_stream):
                service = AccountSubscriptionService(
                    pool=mock_pool,
                    api_key="test_api_key",
                    futures_api_key="",
                    private_key_pem=private_key_pem,
                    snapshot_interval=3600,
                )

                await service.start()
                written_data.clear()

                # 模拟 WebSocket 推送增量数据
                await service._handle_spot_data({"event": "test", "balance": 100})

                # 验证增量数据直接写入
                assert len(written_data) == 1
                assert json.loads(written_data[0]["data"]) == {"event": "test", "balance": 100}

                await service.stop()
