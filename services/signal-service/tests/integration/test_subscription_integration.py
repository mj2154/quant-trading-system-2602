"""
集成测试 - Signal-Service 订阅管理

测试 signal-service 的订阅操作与数据库 realtime_data 表的交互。
需要在运行 Docker 数据库的环境中执行。
"""

import pytest
import asyncio
import asyncpg
import os
from datetime import datetime

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
        # 清理 signal-service 创建的测试数据
        await conn.execute("""
            DELETE FROM realtime_data
            WHERE subscription_key LIKE 'SIGNAL_TEST:%'
            OR subscription_key LIKE 'TEST:SIGNAL:%'
        """)
    yield
    # 测试后清理
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM realtime_data
            WHERE subscription_key LIKE 'SIGNAL_TEST:%'
            OR subscription_key LIKE 'TEST:SIGNAL:%'
        """)


@pytest.fixture
def repository(pool):
    """创建仓储实例"""
    return RealtimeDataRepository(pool)


class TestSignalServiceSubscriptionIntegration:
    """Signal-Service 订阅集成测试"""

    @pytest.mark.asyncio
    async def test_insert_subscription_creates_record(self, repository, clean_db):
        """测试插入订阅创建数据库记录"""
        subscription_key = "SIGNAL_TEST:BINANCE:BTCUSDT@KLINE_1m"
        data_type = "KLINE"

        result = await repository.insert_subscription(subscription_key, data_type)

        # 应该返回记录 ID
        assert result > 0

        # 验证数据库记录
        record = await repository.get_by_subscription_key(subscription_key)
        assert record is not None
        assert record.subscription_key == subscription_key
        assert record.data_type == "KLINE"
        assert "signal-service" in record.subscribers

    @pytest.mark.asyncio
    async def test_insert_subscription_idempotent(self, repository, clean_db):
        """测试重复插入是幂等的"""
        subscription_key = "SIGNAL_TEST:BINANCE:BTCUSDT@KLINE_1m"
        data_type = "KLINE"

        # 第一次插入
        result1 = await repository.insert_subscription(subscription_key, data_type)
        # 第二次插入
        result2 = await repository.insert_subscription(subscription_key, data_type)

        # 应该返回相同的 ID
        assert result1 == result2

        # 验证数据库中只有一个该订阅者
        record = await repository.get_by_subscription_key(subscription_key)
        signal_count = record.subscribers.count("signal-service") if record.subscribers else 0
        assert signal_count == 1

    @pytest.mark.asyncio
    async def test_get_kline_subscriptions(self, repository, clean_db):
        """测试获取所有 KLINE 订阅"""
        # 创建一些 KLINE 订阅
        await repository.insert_subscription("SIGNAL_TEST:BINANCE:BTCUSDT@KLINE_1m", "KLINE")
        await repository.insert_subscription("SIGNAL_TEST:BINANCE:ETHUSDT@KLINE_5m", "KLINE")
        await repository.insert_subscription("SIGNAL_TEST:BINANCE:BNBUSDT@QUOTES", "QUOTES")  # 不应该包含

        result = await repository.get_kline_subscriptions()

        # 应该只返回 KLINE 类型的订阅
        assert len(result) >= 2
        for record in result:
            assert record.data_type == "KLINE"

    @pytest.mark.asyncio
    async def test_insert_multiple_symbols(self, repository, clean_db):
        """测试插入多个交易对订阅"""
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT"]
        interval = "1m"

        for symbol in symbols:
            subscription_key = f"SIGNAL_TEST:BINANCE:{symbol}@KLINE_{interval}"
            await repository.insert_subscription(subscription_key, "KLINE")

        # 验证所有订阅都在数据库
        result = await repository.get_all()
        signal_subscriptions = [r for r in result if r.subscription_key.startswith("SIGNAL_TEST:BINANCE:")]
        assert len(signal_subscriptions) == 4


class TestSignalServiceSubscriberId:
    """验证 Signal-Service 订阅者标识"""

    def test_subscriber_id_is_signal_service(self, repository):
        """验证订阅源标识正确"""
        assert repository.SUBSCRIBER_ID == "signal-service"


class TestSignalServiceAndApiServiceCoexistence:
    """测试 Signal-Service 和 API-Service 订阅共存"""

    @pytest.mark.asyncio
    async def test_both_services_can_subscribe(self, pool, repository, clean_db):
        """测试两个服务都可以订阅同一键"""
        from src.db.realtime_data_repository import RealtimeDataRepository as ApiRealtimeDataRepository

        api_repository = ApiRealtimeDataRepository(pool)

        subscription_key = "TEST:SIGNAL:BINANCE:BTCUSDT@KLINE_1m"

        # Signal-Service 订阅
        await repository.insert_subscription(subscription_key, "KLINE")

        # API-Service 订阅
        await api_repository.add_subscription(subscription_key, "KLINE", "api-service")

        # 验证两个订阅者都在
        record = await repository.get_by_subscription_key(subscription_key)
        assert record is not None
        assert "signal-service" in record.subscribers
        assert "api-service" in record.subscribers

    @pytest.mark.asyncio
    async def test_get_kline_subscriptions_excludes_other_types(self, repository, clean_db):
        """测试 get_kline_subscriptions 只返回 KLINE 类型"""
        # 创建混合类型的订阅
        await repository.insert_subscription("SIGNAL_TEST:BINANCE:BTCUSDT@KLINE_1m", "KLINE")
        await repository.insert_subscription("SIGNAL_TEST:BINANCE:ETHUSDT@KLINE_5m", "KLINE")
        await repository.insert_subscription("SIGNAL_TEST:BINANCE:BNBUSDT@QUOTES", "QUOTES")
        await repository.insert_subscription("SIGNAL_TEST:BINANCE:XRPUSDT@TRADE", "TRADE")

        result = await repository.get_kline_subscriptions()

        # 应该只返回 KLINE 订阅
        for record in result:
            assert record.data_type == "KLINE"
