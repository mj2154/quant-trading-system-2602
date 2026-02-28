"""
测试 Signal-Service 实时数据仓储

验证 signal-service 的订阅操作正确维护 realtime_data 表。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.db.realtime_data_repository import RealtimeDataRepository, RealtimeDataRecord


class TestRealtimeDataRepositoryInsertSubscription:
    """测试 insert_subscription 方法"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库 - 确保所有方法都是异步的"""
        db = MagicMock()
        db.execute = AsyncMock()
        db.fetchrow = AsyncMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        """创建仓储实例"""
        return RealtimeDataRepository(mock_db)

    @pytest.mark.asyncio
    async def test_insert_subscription_new_key(self, repository, mock_db):
        """测试插入新订阅键 - UPDATE 0 行时执行 INSERT"""
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"
        data_type = "KLINE"

        # 使用 side_effect 模拟多次调用返回不同值
        mock_db.execute.side_effect = ["UPDATE 0", "INSERT 0 1"]
        mock_db.fetchrow.return_value = {"id": 1}

        result = await repository.insert_subscription(subscription_key, data_type)

        # 应该执行 UPDATE（尝试追加 subscribers）
        assert mock_db.execute.call_count >= 1
        first_call_args = mock_db.execute.call_args_list[0][0]
        assert "UPDATE realtime_data" in first_call_args[0]
        assert first_call_args[1] == repository.SUBSCRIBER_ID  # signal-service
        assert first_call_args[2] == subscription_key

        # 因为 UPDATE 0 行，执行 INSERT（需要检查 execute 被调用了2次）
        assert mock_db.execute.call_count == 2, "UPDATE 0 后应该执行 INSERT"
        insert_call_args = mock_db.execute.call_args_list[1][0]
        assert "INSERT INTO realtime_data" in insert_call_args[0]

        # fetchrow 应该被调用来获取 id（因为 insert_result 包含 "INSERT"）
        assert mock_db.fetchrow.called
        assert result == 1

    @pytest.mark.asyncio
    async def test_insert_subscription_existing_key(self, repository, mock_db):
        """测试插入已存在的订阅键（幂等性）"""
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"
        data_type = "KLINE"

        # UPDATE 返回更新成功
        mock_db.execute.return_value = "UPDATE 1"
        mock_db.fetchrow.return_value = {"id": 1}

        result = await repository.insert_subscription(subscription_key, data_type)

        # 应该执行 UPDATE
        mock_db.execute.assert_called_once()

        # 因为 UPDATE 成功，执行一次 fetchrow 获取 id
        assert mock_db.fetchrow.call_count == 1
        assert result == 1

    @pytest.mark.asyncio
    async def test_insert_subscription_appends_subscriber(self, repository, mock_db):
        """测试追加 subscribers 数组（幂等性）- 对于新键会执行 UPDATE 然后 INSERT"""
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"
        data_type = "KLINE"

        # 新键：UPDATE 返回 0
        mock_db.execute.return_value = "UPDATE 0"
        mock_db.fetchrow.return_value = {"id": 1}

        await repository.insert_subscription(subscription_key, data_type)

        # 验证第一次 UPDATE 使用 ARRAY_APPEND 和 ARRAY_REMOVE
        first_call_args = mock_db.execute.call_args_list[0][0]
        update_sql = first_call_args[0]
        assert "ARRAY_APPEND" in update_sql
        assert "ARRAY_REMOVE" in update_sql

    @pytest.mark.asyncio
    async def test_insert_subscription_sets_data_type(self, repository, mock_db):
        """测试插入时设置正确的数据类型"""
        subscription_key = "BINANCE:BTCUSDT@KLINE_5m"
        data_type = "KLINE"

        # 新键：UPDATE 返回 0
        mock_db.execute.return_value = "UPDATE 0"
        mock_db.fetchrow.return_value = {"id": 1}

        await repository.insert_subscription(subscription_key, data_type)

        # 验证 INSERT 使用正确的 data_type
        # 需要找到 INSERT 语句的调用（第二次 execute 调用）
        insert_found = False
        for call in mock_db.execute.call_args_list:
            args = call[0]
            if "INSERT INTO realtime_data" in args[0]:
                insert_found = True
                break
        assert insert_found, "应该调用 INSERT INTO realtime_data"


class TestRealtimeDataRepositoryGetBySubscriptionKey:
    """测试 get_by_subscription_key 方法"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库"""
        db = MagicMock()
        db.fetchrow = AsyncMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        """创建仓储实例"""
        return RealtimeDataRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_by_subscription_key_found(self, repository, mock_db):
        """测试获取存在的订阅"""
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"
        mock_db.fetchrow.return_value = {
            "id": 1,
            "subscription_key": subscription_key,
            "data_type": "KLINE",
            "data": {"close": 50000.0},
            "event_time": datetime.now(),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "subscribers": ["signal-service"],
        }

        result = await repository.get_by_subscription_key(subscription_key)

        assert result is not None
        assert result.subscription_key == subscription_key
        assert result.subscribers == ["signal-service"]

    @pytest.mark.asyncio
    async def test_get_by_subscription_key_not_found(self, repository, mock_db):
        """测试获取不存在的订阅"""
        mock_db.fetchrow.return_value = None

        result = await repository.get_by_subscription_key("NONEXISTENT")

        assert result is None


class TestRealtimeDataRepositoryGetKlineSubscriptions:
    """测试 get_kline_subscriptions 方法"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库"""
        db = MagicMock()
        db.fetch = AsyncMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        """创建仓储实例"""
        return RealtimeDataRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_kline_subscriptions(self, repository, mock_db):
        """测试获取所有 KLINE 类型订阅"""
        mock_db.fetch.return_value = [
            {
                "id": 1,
                "subscription_key": "BINANCE:BTCUSDT@KLINE_1m",
                "data_type": "KLINE",
                "data": {},
                "event_time": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "subscribers": ["signal-service"],
            },
            {
                "id": 2,
                "subscription_key": "BINANCE:ETHUSDT@KLINE_1m",
                "data_type": "KLINE",
                "data": {},
                "event_time": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "subscribers": ["signal-service"],
            },
        ]

        result = await repository.get_kline_subscriptions()

        assert len(result) == 2
        assert all(r.data_type == "KLINE" for r in result)


class TestRealtimeDataRepositoryGetAll:
    """测试 get_all 方法"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库"""
        db = MagicMock()
        db.fetch = AsyncMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        """创建仓储实例"""
        return RealtimeDataRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_all_returns_all_records(self, repository, mock_db):
        """测试获取所有实时数据记录"""
        mock_db.fetch.return_value = [
            {
                "id": 1,
                "subscription_key": "BINANCE:BTCUSDT@KLINE_1m",
                "data_type": "KLINE",
                "data": {},
                "event_time": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "subscribers": ["signal-service"],
            },
        ]

        result = await repository.get_all()

        assert len(result) == 1
        mock_db.fetch.assert_called_once()


class TestRealtimeDataRepositorySubscriberId:
    """测试 SUBSCRIBER_ID"""

    def test_subscriber_id_is_signal_service(self):
        """验证订阅源标识"""
        assert RealtimeDataRepository.SUBSCRIBER_ID == "signal-service"
