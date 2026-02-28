"""
集成测试 - API-Service 订阅管理

测试订阅/取消订阅与数据库 realtime_data 表的交互。
需要在运行 Docker 数据库的环境中执行。
"""

import pytest
import asyncio
import asyncpg
import os
from datetime import datetime

from src.gateway.subscription_manager import SubscriptionManager
from src.db.realtime_data_repository import RealtimeDataRepository


# 数据库连接配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "trading_db"),
    "user": os.getenv("DB_USER", "dbuser"),
    "password": os.getenv("DB_PASSWORD", "pass"),
}


@pytest.fixture(scope="module")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def pool():
    """创建数据库连接池"""
    try:
        pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=2)
        yield pool
        await pool.close()
    except Exception as e:
        pytest.skip(f"数据库不可用: {e}")


@pytest.fixture
async def clean_db(pool):
    """清理测试数据"""
    async with pool.acquire() as conn:
        # 清理 api-service 创建的测试数据
        await conn.execute("""
            DELETE FROM realtime_data
            WHERE subscription_key LIKE 'TEST:%'
        """)
    yield
    # 测试后清理
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM realtime_data
            WHERE subscription_key LIKE 'TEST:%'
        """)


@pytest.fixture
def repository(pool):
    """创建仓储实例"""
    return RealtimeDataRepository(pool)


@pytest.fixture
def manager(pool):
    """创建订阅管理器实例"""
    return SubscriptionManager(pool)


class TestApiServiceSubscriptionIntegration:
    """API-Service 订阅集成测试"""

    @pytest.mark.asyncio
    async def test_subscribe_creates_db_record(self, manager, repository, clean_db):
        """测试订阅创建数据库记录"""
        client_id = "test-client-1"
        subscription_key = "TEST:BINANCE:BTCUSDT@KLINE_1m"

        # 订阅
        result = await manager.subscribe(client_id, subscription_key)

        # 应该返回 True（触发了 INSERT）
        assert result is True

        # 验证数据库记录
        record = await repository.get_subscription(subscription_key)
        assert record is not None
        assert record["subscription_key"] == subscription_key
        assert "api-service" in record["subscribers"]

    @pytest.mark.asyncio
    async def test_subscribe_idempotent(self, manager, repository, clean_db):
        """测试重复订阅是幂等的"""
        client_id = "test-client-1"
        subscription_key = "TEST:BINANCE:BTCUSDT@KLINE_1m"

        # 第一次订阅
        await manager.subscribe(client_id, subscription_key)
        # 第二次订阅
        result = await manager.subscribe(client_id, subscription_key)

        # 应该返回 False（没有新 INSERT）
        assert result is False

        # 验证数据库中只有一个该客户端
        record = await repository.get_subscription(subscription_key)
        assert record["subscribers"].count(client_id) == 1

    @pytest.mark.asyncio
    async def test_multiple_clients_subscribe(self, manager, repository, clean_db):
        """测试多个客户端订阅同一键"""
        client_id_1 = "test-client-1"
        client_id_2 = "test-client-2"
        subscription_key = "TEST:BINANCE:BTCUSDT@KLINE_1m"

        # 两个客户端都订阅
        await manager.subscribe(client_id_1, subscription_key)
        await manager.subscribe(client_id_2, subscription_key)

        # 验证数据库
        record = await repository.get_subscription(subscription_key)
        assert len(record["subscribers"]) >= 2

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_from_db(self, manager, repository, clean_db):
        """测试取消订阅从数据库移除"""
        client_id = "test-client-1"
        subscription_key = "TEST:BINANCE:BTCUSDT@KLINE_1m"

        # 先订阅
        await manager.subscribe(client_id, subscription_key)

        # 再取消
        result = await manager.unsubscribe(client_id, subscription_key)

        # 应该返回 True（触发了 DELETE）
        assert result is True

        # 验证数据库记录被删除
        record = await repository.get_subscription(subscription_key)
        assert record is None

    @pytest.mark.asyncio
    async def test_unsubscribe_keeps_other_subscribers(self, manager, repository, clean_db):
        """测试取消订阅保留其他订阅者"""
        client_id_1 = "test-client-1"
        client_id_2 = "test-client-2"
        subscription_key = "TEST:BINANCE:BTCUSDT@KLINE_1m"

        # 两个客户端都订阅
        await manager.subscribe(client_id_1, subscription_key)
        await manager.subscribe(client_id_2, subscription_key)

        # 客户端1取消
        result = await manager.unsubscribe(client_id_1, subscription_key)

        # 应该返回 False（有其他订阅者，不删除）
        assert result is False

        # 验证数据库记录仍在
        record = await repository.get_subscription(subscription_key)
        assert record is not None

    @pytest.mark.asyncio
    async def test_unsubscribe_all(self, manager, repository, clean_db):
        """测试取消所有订阅"""
        client_id = "test-client-1"

        # 订阅多个键
        await manager.subscribe(client_id, "TEST:BINANCE:BTCUSDT@KLINE_1m")
        await manager.subscribe(client_id, "TEST:BINANCE:ETHUSDT@KLINE_1m")
        await manager.subscribe(client_id, "TEST:BINANCE:BNBUSDT@QUOTES")

        # 取消所有
        deleted_keys = await manager.unsubscribe_all(client_id)

        # 应该删除3条记录
        assert len(deleted_keys) == 3

        # 验证数据库
        assert await repository.get_subscription("TEST:BINANCE:BTCUSDT@KLINE_1m") is None
        assert await repository.get_subscription("TEST:BINANCE:ETHUSDT@KLINE_1m") is None
        assert await repository.get_subscription("TEST:BINANCE:BNBUSDT@QUOTES") is None

    @pytest.mark.asyncio
    async def test_batch_subscribe_and_unsubscribe(self, manager, repository, clean_db):
        """测试批量订阅和取消"""
        client_id = "test-client-batch"

        subscription_keys = [
            "TEST:BINANCE:BTCUSDT@KLINE_1m",
            "TEST:BINANCE:ETHUSDT@KLINE_1m",
            "TEST:BINANCE:BNBUSDT@QUOTES",
        ]

        # 批量订阅
        inserted_count = await manager.subscribe_batch(client_id, subscription_keys)
        assert inserted_count == 3

        # 验证所有记录都在数据库
        for key in subscription_keys:
            record = await repository.get_subscription(key)
            assert record is not None

        # 批量取消
        deleted_count = await manager.unsubscribe_batch(client_id, subscription_keys)
        assert deleted_count == 3

        # 验证所有记录都被删除
        for key in subscription_keys:
            record = await repository.get_subscription(key)
            assert record is None

    @pytest.mark.asyncio
    async def test_truncate_and_notify_clean(self, manager, repository, clean_db):
        """测试清空所有订阅"""
        client_id = "test-client-truncate"

        # 创建一些订阅
        await manager.subscribe(client_id, "TEST:BINANCE:BTCUSDT@KLINE_1m")
        await manager.subscribe(client_id, "TEST:BINANCE:ETHUSDT@KLINE_1m")

        # 清空所有
        await manager.truncate_and_notify_clean()

        # 验证内存和数据库都被清空
        assert manager.get_key_count() == 0
        assert len(manager._db_keys) == 0

        # 只删除 api-service 的订阅，TEST 键应该被删除
        assert await repository.get_subscription("TEST:BINANCE:BTCUSDT@KLINE_1m") is None


class TestApiServiceDifferentDataTypes:
    """测试不同数据类型"""

    @pytest.mark.asyncio
    async def test_subscribe_kline_type(self, manager, repository, clean_db):
        """测试 KLINE 类型订阅"""
        client_id = "test-client-kline"
        subscription_key = "TEST:BINANCE:BTCUSDT@KLINE_1m"

        await manager.subscribe(client_id, subscription_key)

        record = await repository.get_subscription(subscription_key)
        assert record["data_type"] == "KLINE"

    @pytest.mark.asyncio
    async def test_subscribe_quotes_type(self, manager, repository, clean_db):
        """测试 QUOTES 类型订阅"""
        client_id = "test-client-quotes"
        subscription_key = "TEST:BINANCE:BTCUSDT@QUOTES"

        await manager.subscribe(client_id, subscription_key)

        record = await repository.get_subscription(subscription_key)
        assert record["data_type"] == "QUOTES"

    @pytest.mark.asyncio
    async def test_subscribe_trade_type(self, manager, repository, clean_db):
        """测试 TRADE 类型订阅"""
        client_id = "test-client-trade"
        subscription_key = "TEST:BINANCE:BTCUSDT@TRADE"

        await manager.subscribe(client_id, subscription_key)

        record = await repository.get_subscription(subscription_key)
        assert record["data_type"] == "TRADE"
