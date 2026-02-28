"""
集成测试 - binance-service 账户信息仓储

测试 save_account_info() 方法的数据库操作：
1. 写入新的账户信息
2. 覆盖更新已存在的账户信息
3. 数据正确性验证

需要在运行 Docker 数据库的环境中执行。
"""

import pytest
import asyncio
import asyncpg
import os
import json
from datetime import datetime, timezone


# 数据库连接配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "trading_db"),
    "user": os.getenv("DB_USER", "dbuser"),
    "password": os.getenv("DB_PASSWORD", "pass"),
}


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

    # 直接导入 tasks_repository 模块而不触发 __init__.py
    test_dir = os.path.dirname(__file__)
    src_dir = os.path.join(test_dir, '..', 'src')
    sys.path.insert(0, src_dir)

    # 临时禁用 __init__.py 以避免相对导入问题
    import importlib.util

    # 直接加载 tasks_repository.py
    spec = importlib.util.spec_from_file_location(
        "tasks_repository",
        os.path.join(src_dir, "db", "tasks_repository.py")
    )
    tasks_repo_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tasks_repo_module)

    TasksRepository = tasks_repo_module.TasksRepository
    return TasksRepository(pool)


class TestBinanceServiceSaveAccountInfo:
    """binance-service 账户信息保存测试"""

    @pytest.mark.asyncio
    async def test_save_account_info_new_record(self, repository, clean_db):
        """测试写入新的账户信息"""
        # 测试数据
        account_type = "SPOT"
        data = {
            "accountType": "SPOT",
            "balances": [
                {"asset": "BTC", "free": "1.0", "locked": "0.5"},
                {"asset": "USDT", "free": "1000.0", "locked": "0.0"},
            ],
            "canTrade": True,
            "updateTime": 1234567890,
        }
        update_time = 1234567890

        # 执行保存
        await repository.save_account_info(
            account_type=account_type,
            data=data,
            update_time=update_time,
        )

        # 验证数据库记录
        async with repository._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT account_type, data, update_time FROM account_info WHERE account_type = $1",
                account_type,
            )

        assert row is not None
        assert row["account_type"] == account_type
        assert row["update_time"] == update_time
        # data 是 JSONB 类型，asyncpg可能返回字符串，需要转换
        data = row["data"]
        if isinstance(data, str):
            data = json.loads(data)
        assert data["accountType"] == "SPOT"
        assert len(data["balances"]) == 2

    @pytest.mark.asyncio
    async def test_save_account_info_update_existing(self, repository, clean_db):
        """测试覆盖更新已存在的账户信息"""
        account_type = "FUTURES"
        original_data = {
            "accountType": "FUTURES",
            "totalMarginBalance": "10000.0",
            "updateTime": 1111111111,
        }
        updated_data = {
            "accountType": "FUTURES",
            "totalMarginBalance": "20000.0",
            "updateTime": 2222222222,
        }

        # 第一次写入（新增）
        await repository.save_account_info(
            account_type=account_type,
            data=original_data,
            update_time=1111111111,
        )

        # 验证第一次写入
        async with repository._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data, update_time FROM account_info WHERE account_type = $1",
                account_type,
            )
            data = row["data"]
            if isinstance(data, str):
                data = json.loads(data)
            assert data["totalMarginBalance"] == "10000.0"
            assert row["update_time"] == 1111111111

        # 第二次写入（覆盖更新）
        await repository.save_account_info(
            account_type=account_type,
            data=updated_data,
            update_time=2222222222,
        )

        # 验证覆盖更新 - 应该只有一条记录
        async with repository._pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM account_info WHERE account_type = $1",
                account_type,
            )
            assert count == 1

            # 验证数据已更新
            row = await conn.fetchrow(
                "SELECT data, update_time FROM account_info WHERE account_type = $1",
                account_type,
            )
            data = row["data"]
            if isinstance(data, str):
                data = json.loads(data)
            assert data["totalMarginBalance"] == "20000.0"
            assert row["update_time"] == 2222222222

    @pytest.mark.asyncio
    async def test_save_account_info_multiple_types(self, repository, clean_db):
        """测试同时保存多个账户类型"""
        spot_data = {"accountType": "SPOT", "balances": []}
        futures_data = {"accountType": "FUTURES", "totalMarginBalance": "5000.0"}

        # 保存两种账户类型
        await repository.save_account_info("SPOT", spot_data, 1000)
        await repository.save_account_info("FUTURES", futures_data, 2000)

        # 验证两条记录
        async with repository._pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM account_info")
            assert count == 2

            spot_row = await conn.fetchrow(
                "SELECT data FROM account_info WHERE account_type = 'SPOT'"
            )
            futures_row = await conn.fetchrow(
                "SELECT data FROM account_info WHERE account_type = 'FUTURES'"
            )

            spot_data = spot_row["data"]
            futures_data = futures_row["data"]
            if isinstance(spot_data, str):
                spot_data = json.loads(spot_data)
            if isinstance(futures_data, str):
                futures_data = json.loads(futures_data)
            assert spot_data["accountType"] == "SPOT"
            assert futures_data["accountType"] == "FUTURES"

    @pytest.mark.asyncio
    async def test_save_account_info_with_complex_data(self, repository, clean_db):
        """测试保存复杂的账户数据"""
        account_type = "SPOT"
        complex_data = {
            "accountType": "SPOT",
            "balances": [
                {"asset": "BTC", "free": "0.12345678", "locked": "0.00000001"},
                {"asset": "ETH", "free": "12.34567890", "locked": "0.00000000"},
                {"asset": "USDT", "free": "999999.99999999", "locked": "0.00000000"},
            ],
            "canTrade": True,
            "canWithdraw": True,
            "canDeposit": False,
            "permissions": ["SPOT", "MARGIN"],
            "updateTime": 1700000000000,
        }

        await repository.save_account_info(
            account_type=account_type,
            data=complex_data,
            update_time=1700000000000,
        )

        # 验证数据完整性
        async with repository._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM account_info WHERE account_type = $1",
                account_type,
            )

        saved_data = row["data"]
        if isinstance(saved_data, str):
            saved_data = json.loads(saved_data)
        assert saved_data["accountType"] == "SPOT"
        assert saved_data["canTrade"] is True
        assert saved_data["canWithdraw"] is True
        assert saved_data["canDeposit"] is False
        assert saved_data["permissions"] == ["SPOT", "MARGIN"]
        assert len(saved_data["balances"]) == 3
        # 验证高精度数值保留
        assert saved_data["balances"][0]["free"] == "0.12345678"
        assert saved_data["balances"][2]["free"] == "999999.99999999"

    @pytest.mark.asyncio
    async def test_save_account_info_null_update_time(self, repository, clean_db):
        """测试 update_time 为空的情况"""
        account_type = "SPOT"
        data = {"accountType": "SPOT", "balances": []}

        await repository.save_account_info(
            account_type=account_type,
            data=data,
            update_time=None,
        )

        # 验证 update_time 为 NULL
        async with repository._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT update_time FROM account_info WHERE account_type = $1",
                account_type,
            )
            assert row["update_time"] is None

    @pytest.mark.asyncio
    async def test_save_account_info_updated_at_is_set(self, repository, clean_db):
        """测试 updated_at 字段自动设置"""
        account_type = "SPOT"
        data = {"accountType": "SPOT", "balances": []}

        # 记录执行前的时间
        before_save = datetime.now(timezone.utc)

        await repository.save_account_info(
            account_type=account_type,
            data=data,
            update_time=1000,
        )

        # 验证 updated_at 已设置
        async with repository._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT updated_at FROM account_info WHERE account_type = $1",
                account_type,
            )

        assert row["updated_at"] is not None
        assert row["updated_at"] >= before_save
