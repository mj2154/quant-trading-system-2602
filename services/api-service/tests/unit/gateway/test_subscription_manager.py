"""
测试 API-Service 订阅管理器

验证订阅/取消订阅功能正确操作数据库 realtime_data 表。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.gateway.subscription_manager import SubscriptionManager


class TestSubscriptionManagerSubscribe:
    """测试 subscribe 方法"""

    @pytest.fixture
    def mock_repository(self):
        """创建模拟仓储"""
        repo = MagicMock()
        repo.add_subscription = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def manager(self, mock_repository):
        """创建订阅管理器实例"""
        # 创建时不传 pool，使用默认构造
        manager = SubscriptionManager.__new__(SubscriptionManager)
        manager._pool = MagicMock()
        manager._repository = mock_repository
        manager._lock = asyncio.Lock()
        manager._subscriptions = {}
        manager._db_keys = set()
        return manager

    @pytest.mark.asyncio
    async def test_subscribe_adds_to_memory(self, manager):
        """测试订阅时客户端被添加到内存字典"""
        client_id = "client-1"
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"

        await manager.subscribe(client_id, subscription_key)

        # 客户端应该被添加到内存字典
        assert client_id in manager._subscriptions[subscription_key]
        assert subscription_key in manager._db_keys

    @pytest.mark.asyncio
    async def test_subscribe_multiple_clients_same_key(self, manager):
        """测试多个客户端订阅同一键"""
        client_id_1 = "client-1"
        client_id_2 = "client-2"
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"

        # 第一个客户端订阅
        await manager.subscribe(client_id_1, subscription_key)
        # 第二个客户端订阅
        result = await manager.subscribe(client_id_2, subscription_key)

        # 两个客户端都在内存字典中
        assert len(manager._subscriptions[subscription_key]) == 2
        assert client_id_1 in manager._subscriptions[subscription_key]
        assert client_id_2 in manager._subscriptions[subscription_key]

    @pytest.mark.asyncio
    async def test_subscribe_adds_to_db_keys(self, manager):
        """测试订阅键被添加到 _db_keys 集合"""
        client_id = "client-1"
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"

        await manager.subscribe(client_id, subscription_key)

        assert subscription_key in manager._db_keys

    @pytest.mark.asyncio
    async def test_subscribe_parses_kline_type(self, manager, mock_repository):
        """测试 KLINE 类型订阅键解析"""
        client_id = "client-1"
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"

        await manager.subscribe(client_id, subscription_key)

        # 应该以 "KLINE" 类型调用 add_subscription
        mock_repository.add_subscription.assert_called_once_with(subscription_key, "KLINE", "api-service")

    @pytest.mark.asyncio
    async def test_subscribe_parses_quotes_type(self, manager, mock_repository):
        """测试 QUOTES 类型订阅键解析"""
        client_id = "client-1"
        subscription_key = "BINANCE:BTCUSDT@QUOTES"

        await manager.subscribe(client_id, subscription_key)

        # 应该以 "QUOTES" 类型调用 add_subscription
        mock_repository.add_subscription.assert_called_once_with(subscription_key, "QUOTES", "api-service")

    @pytest.mark.asyncio
    async def test_subscribe_idempotent(self, manager):
        """测试重复订阅是幂等的"""
        client_id = "client-1"
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"

        # 第一次订阅
        await manager.subscribe(client_id, subscription_key)
        # 第二次订阅同一键
        result = await manager.subscribe(client_id, subscription_key)

        # 客户端只在字典中一次
        assert client_id in manager._subscriptions[subscription_key]


class TestSubscriptionManagerUnsubscribe:
    """测试 unsubscribe 方法"""

    @pytest.fixture
    def mock_repository(self):
        """创建模拟仓储"""
        repo = MagicMock()
        repo.add_subscription = AsyncMock(return_value=True)
        repo.remove_subscription = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def manager(self, mock_repository):
        """创建订阅管理器实例"""
        manager = SubscriptionManager.__new__(SubscriptionManager)
        manager._pool = MagicMock()
        manager._repository = mock_repository
        manager._lock = asyncio.Lock()
        manager._subscriptions = {}
        manager._db_keys = set()
        return manager

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_from_memory(self, manager):
        """测试取消订阅从内存字典移除客户端"""
        client_id = "client-1"
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"

        # 先订阅
        await manager.subscribe(client_id, subscription_key)
        # 再取消订阅
        await manager.unsubscribe(client_id, subscription_key)

        # 客户端应该被移除
        assert client_id not in manager._subscriptions.get(subscription_key, set())

    @pytest.mark.asyncio
    async def test_unsubscribe_keeps_other_clients(self, manager):
        """测试取消订阅保留其他客户端"""
        client_id_1 = "client-1"
        client_id_2 = "client-2"
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"

        # 两个客户端都订阅
        await manager.subscribe(client_id_1, subscription_key)
        await manager.subscribe(client_id_2, subscription_key)

        # 客户端1取消
        await manager.unsubscribe(client_id_1, subscription_key)

        # 客户端2应该还在
        assert client_id_2 in manager._subscriptions[subscription_key]
        assert subscription_key in manager._db_keys  # 仍在数据库中

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_key(self, manager):
        """测试取消不存在的订阅"""
        result = await manager.unsubscribe("client-1", "BINANCE:ETHUSDT@KLINE_1m")
        # 应该返回 False，不抛出异常
        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_db_key_when_empty(self, manager, mock_repository):
        """测试最后一个客户端取消时删除数据库记录"""
        client_id = "client-1"
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"

        # 订阅
        await manager.subscribe(client_id, subscription_key)
        assert subscription_key in manager._db_keys

        # 取消订阅
        result = await manager.unsubscribe(client_id, subscription_key)

        # 应该触发数据库删除
        assert result is True
        mock_repository.remove_subscription.assert_called_once_with(subscription_key, "api-service")
        assert subscription_key not in manager._db_keys


class TestSubscriptionManagerBatch:
    """测试批量订阅方法"""

    @pytest.fixture
    def mock_repository(self):
        """创建模拟仓储"""
        repo = MagicMock()
        repo.add_subscription = AsyncMock(return_value=True)
        repo.remove_subscription = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def manager(self, mock_repository):
        """创建订阅管理器实例"""
        manager = SubscriptionManager.__new__(SubscriptionManager)
        manager._pool = MagicMock()
        manager._repository = mock_repository
        manager._lock = asyncio.Lock()
        manager._subscriptions = {}
        manager._db_keys = set()
        return manager

    @pytest.mark.asyncio
    async def test_subscribe_batch(self, manager):
        """测试批量订阅"""
        client_id = "client-1"
        subscription_keys = [
            "BINANCE:BTCUSDT@KLINE_1m",
            "BINANCE:ETHUSDT@KLINE_1m",
            "BINANCE:BNBUSDT@QUOTES",
        ]

        await manager.subscribe_batch(client_id, subscription_keys)

        for key in subscription_keys:
            assert client_id in manager._subscriptions[key]

    @pytest.mark.asyncio
    async def test_unsubscribe_batch(self, manager):
        """测试批量取消订阅"""
        client_id = "client-1"
        subscription_keys = [
            "BINANCE:BTCUSDT@KLINE_1m",
            "BINANCE:ETHUSDT@KLINE_1m",
            "BINANCE:BNBUSDT@QUOTES",
        ]

        # 先订阅
        await manager.subscribe_batch(client_id, subscription_keys)

        # 再批量取消
        await manager.unsubscribe_batch(client_id, subscription_keys)

        for key in subscription_keys:
            assert key not in manager._subscriptions


class TestSubscriptionManagerUnsubscribeAll:
    """测试 unsubscribe_all 方法"""

    @pytest.fixture
    def mock_repository(self):
        """创建模拟仓储"""
        repo = MagicMock()
        repo.add_subscription = AsyncMock(return_value=True)
        repo.remove_subscription = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def manager(self, mock_repository):
        """创建订阅管理器实例"""
        manager = SubscriptionManager.__new__(SubscriptionManager)
        manager._pool = MagicMock()
        manager._repository = mock_repository
        manager._lock = asyncio.Lock()
        manager._subscriptions = {}
        manager._db_keys = set()
        return manager

    @pytest.mark.asyncio
    async def test_unsubscribe_all_removes_all_subscriptions(self, manager):
        """测试取消所有订阅"""
        client_id = "client-1"

        # 订阅多个键
        await manager.subscribe(client_id, "BINANCE:BTCUSDT@KLINE_1m")
        await manager.subscribe(client_id, "BINANCE:ETHUSDT@KLINE_1m")
        await manager.subscribe(client_id, "BINANCE:BNBUSDT@QUOTES")

        # 取消所有
        deleted_keys = await manager.unsubscribe_all(client_id)

        # 应该返回被删除的键
        assert len(deleted_keys) == 3
        assert manager.get_subscription_count() == 0


class TestSubscriptionManagerDataTypeParsing:
    """测试数据类型解析"""

    @pytest.fixture
    def manager(self):
        """创建订阅管理器实例"""
        manager = SubscriptionManager.__new__(SubscriptionManager)
        manager._pool = MagicMock()
        manager._repository = MagicMock()
        manager._lock = asyncio.Lock()
        manager._subscriptions = {}
        manager._db_keys = set()
        return manager

    def test_parse_kline_type(self, manager):
        """测试 KLINE 类型解析"""
        assert manager._parse_data_type_from_key("BINANCE:BTCUSDT@KLINE_1m") == "KLINE"
        assert manager._parse_data_type_from_key("BINANCE:BTCUSDT@KLINE_5") == "KLINE"

    def test_parse_quotes_type(self, manager):
        """测试 QUOTES 类型解析"""
        assert manager._parse_data_type_from_key("BINANCE:BTCUSDT@QUOTES") == "QUOTES"

    def test_parse_trade_type(self, manager):
        """测试 TRADE 类型解析"""
        assert manager._parse_data_type_from_key("BINANCE:BTCUSDT@TRADE") == "TRADE"

    def test_parse_unknown_type(self, manager):
        """测试未知类型解析"""
        assert manager._parse_data_type_from_key("BINANCE:BTCUSDT@UNKNOWN") == "UNKNOWN"


class TestSubscriptionManagerNormalization:
    """测试订阅键标准化"""

    @pytest.fixture
    def manager(self):
        """创建订阅管理器实例"""
        manager = SubscriptionManager.__new__(SubscriptionManager)
        manager._pool = MagicMock()
        manager._repository = MagicMock()
        manager._lock = asyncio.Lock()
        manager._subscriptions = {}
        manager._db_keys = set()
        return manager

    def test_normalize_resolution_1_to_1m(self, manager):
        """测试 1 -> 1m 标准化"""
        result = manager._normalize_subscription_key("BINANCE:BTCUSDT@KLINE_1")
        assert result == "BINANCE:BTCUSDT@KLINE_1m"

    def test_normalize_resolution_60_to_1h(self, manager):
        """测试 60 -> 1h 标准化"""
        result = manager._normalize_subscription_key("BINANCE:BTCUSDT@KLINE_60")
        assert result == "BINANCE:BTCUSDT@KLINE_1h"

    def test_normalize_resolution_already_standardized(self, manager):
        """测试已标准化的键保持不变"""
        key = "BINANCE:BTCUSDT@KLINE_1m"
        result = manager._normalize_subscription_key(key)
        assert result == key

    def test_normalize_quotes_unchanged(self, manager):
        """测试 QUOTES 类型不变化"""
        key = "BINANCE:BTCUSDT@QUOTES"
        result = manager._normalize_subscription_key(key)
        assert result == key
