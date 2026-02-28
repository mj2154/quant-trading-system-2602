"""
集成测试 - api-service 账户信息仓储

测试 get_account_info() 方法的数据库操作：
1. 查询已存在的账户信息
2. 查询不存在的账户信息返回 None
3. 数据格式正确性

需要在运行 Docker 数据库的环境中执行。
"""

import pytest
import asyncio
import asyncpg
import json
import os
from datetime import datetime, timezone


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


@pytest.fixture
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
        await conn.execute("""
            DELETE FROM account_info
            WHERE account_type IN ('SPOT', 'FUTURES')
        """)
    yield
    # 测试后清理
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM account_info
            WHERE account_type IN ('SPOT', 'FUTURES')
        """)


@pytest.fixture
def repository(pool):
    """创建 TasksRepository 实例"""
    import sys
    import os
    # 添加 src 路径
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    from db.tasks_repository import TasksRepository
    return TasksRepository(pool)


class TestApiServiceGetAccountInfo:
    """api-service 账户信息查询测试"""

    @pytest.mark.asyncio
    async def test_get_account_info_existing(self, repository, pool, clean_db):
        """测试查询已存在的账户信息"""
        # 先插入测试数据
        account_type = "SPOT"
        data = {
            "accountType": "SPOT",
            "balances": [
                {"asset": "BTC", "free": "1.0", "locked": "0.5"},
            ],
            "canTrade": True,
        }
        update_time = 1234567890

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO account_info (account_type, data, update_time, updated_at)
                VALUES ($1, $2, $3, $4)
                """,
                account_type,
                json.dumps(data),
                update_time,
                datetime.now(timezone.utc),
            )

        # 执行查询
        result = await repository.get_account_info(account_type)

        # 验证结果 - data可能是字符串，需要转换
        assert result is not None
        data = result["data"]
        if isinstance(data, str):
            data = json.loads(data)
        assert data["accountType"] == "SPOT"
        assert len(data["balances"]) == 1
        assert result["update_time"] == update_time
        assert result["updated_at"] is not None

    @pytest.mark.asyncio
    async def test_get_account_info_not_existing(self, repository, clean_db):
        """测试查询不存在的账户信息返回 None"""
        result = await repository.get_account_info("NONEXISTENT")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_account_info_spot_type(self, repository, pool, clean_db):
        """测试查询 SPOT 账户类型"""
        # 插入 SPOT 数据
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO account_info (account_type, data, update_time)
                VALUES ('SPOT', $1, 1000)
                """,
                json.dumps({"accountType": "SPOT", "balances": []}),
            )

        result = await repository.get_account_info("SPOT")

        assert result is not None
        data = result["data"]
        if isinstance(data, str):
            data = json.loads(data)
        assert data["accountType"] == "SPOT"

    @pytest.mark.asyncio
    async def test_get_account_info_futures_type(self, repository, pool, clean_db):
        """测试查询 FUTURES 账户类型"""
        # 插入 FUTURES 数据
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO account_info (account_type, data, update_time)
                VALUES ('FUTURES', $1, 2000)
                """,
                json.dumps({"accountType": "FUTURES", "totalMarginBalance": "50000.0"}),
            )

        result = await repository.get_account_info("FUTURES")

        assert result is not None
        data = result["data"]
        if isinstance(data, str):
            data = json.loads(data)
        assert data["accountType"] == "FUTURES"
        assert data["totalMarginBalance"] == "50000.0"
        assert result["update_time"] == 2000

    @pytest.mark.asyncio
    async def test_get_account_info_complex_data(self, repository, pool, clean_db):
        """测试查询复杂的账户数据"""
        complex_data = {
            "accountType": "SPOT",
            "balances": [
                {"asset": "BTC", "free": "0.12345678", "locked": "0.00000001"},
                {"asset": "ETH", "free": "12.34567890", "locked": "0.00000000"},
            ],
            "canTrade": True,
            "canWithdraw": True,
            "canDeposit": False,
            "permissions": ["SPOT", "MARGIN"],
            "buyerCommission": "0.001",
            "sellerCommission": "0.001",
        }

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO account_info (account_type, data, update_time)
                VALUES ('SPOT', $1, 1700000000000)
                """,
                json.dumps(complex_data),
            )

        result = await repository.get_account_info("SPOT")

        assert result is not None
        saved_data = result["data"]
        if isinstance(saved_data, str):
            saved_data = json.loads(saved_data)
        assert saved_data["accountType"] == "SPOT"
        assert len(saved_data["balances"]) == 2
        assert saved_data["canTrade"] is True
        assert saved_data["canWithdraw"] is True
        assert saved_data["canDeposit"] is False
        assert saved_data["permissions"] == ["SPOT", "MARGIN"]
        assert saved_data["buyerCommission"] == "0.001"
        assert saved_data["sellerCommission"] == "0.001"

    @pytest.mark.asyncio
    async def test_get_account_info_null_update_time(self, repository, pool, clean_db):
        """测试查询 update_time 为 NULL 的记录"""
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO account_info (account_type, data, update_time)
                VALUES ('SPOT', $1, NULL)
                """,
                json.dumps({"accountType": "SPOT"}),
            )

        result = await repository.get_account_info("SPOT")

        assert result is not None
        assert result["update_time"] is None

    @pytest.mark.asyncio
    async def test_get_account_info_returns_dict_format(self, repository, pool, clean_db):
        """测试返回的是字典格式"""
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO account_info (account_type, data, update_time)
                VALUES ('SPOT', $1, 1000)
                """,
                json.dumps({"accountType": "SPOT", "test": "value"}),
            )

        result = await repository.get_account_info("SPOT")

        # 验证返回类型
        assert isinstance(result, dict)
        assert "data" in result
        assert "update_time" in result
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_get_account_info_updated_at_format(self, repository, pool, clean_db):
        """测试 updated_at 字段返回 ISO 格式字符串"""
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO account_info (account_type, data, update_time, updated_at)
                VALUES ('SPOT', $1, 1000, $2)
                """,
                json.dumps({"accountType": "SPOT"}),
                datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            )

        result = await repository.get_account_info("SPOT")

        assert result is not None
        # updated_at 应该是 ISO 格式字符串
        assert result["updated_at"] is not None
        assert "2024-01-15" in result["updated_at"]
