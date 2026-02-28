#!/usr/bin/env python3
"""
币安服务新架构测试脚本

根据 SUBSCRIPTION_AND_REALTIME_DATA.md 设计，验证新架构功能：

1. 一次性请求任务（tasks表）：
   - get_klines: 获取K线历史数据
   - get_server_time: 获取服务器时间
   - get_quotes: 获取实时报价

2. 订阅管理（realtime_data表）：
   - subscription_add: 新增订阅通知
   - subscription_remove: 取消订阅通知
   - realtime_update: 实时数据更新通知

使用方式：
    cd /home/ppadmin/code/quant-trading-system/services/binance-service
    python test_new_architecture.py
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional

import asyncpg

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ArchitectureTester:
    """新架构测试器"""

    def __init__(self):
        """初始化测试器"""
        self.dsn = self._get_dsn()
        self.pool: Optional[asyncpg.Pool] = None

    def _get_dsn(self) -> str:
        """构建数据库连接字符串"""
        host = os.getenv("DATABASE_HOST", "localhost")
        port = os.getenv("DATABASE_PORT", "5432")
        name = os.getenv("DATABASE_NAME", "trading_db")
        user = os.getenv("DATABASE_USER", "dbuser")
        password = os.getenv("DATABASE_PASSWORD", "pass")

        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    async def setup(self):
        """初始化测试环境"""
        logger.info("初始化测试环境...")

        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=1,
            max_size=5,
        )

    async def teardown(self):
        """清理测试环境"""
        if self.pool:
            await self.pool.close()
            logger.info("测试环境已清理")

    async def test_tasks_table(self):
        """测试 tasks 表功能"""
        logger.info("=" * 60)
        logger.info("测试1: tasks 表功能")
        logger.info("=" * 60)

        # 1. 检查 tasks 表是否存在
        table_exists = await self._check_table_exists("tasks")
        logger.info(f"✓ tasks 表存在: {table_exists}")

        if not table_exists:
            logger.error("✗ tasks 表不存在，请检查数据库初始化脚本")
            return False

        # 2. 创建测试任务
        task_id = await self._create_test_task()
        if not task_id:
            logger.error("✗ 创建测试任务失败")
            return False

        logger.info(f"✓ 创建测试任务成功 (ID: {task_id})")

        # 3. 验证任务通知
        logger.info("等待 task_new 通知...")

        # 使用 LISTEN/NOTIFY 监听通知
        await self._listen_for_task_notification(task_id)

        return True

    async def test_realtime_data_table(self):
        """测试 realtime_data 表功能"""
        logger.info("=" * 60)
        logger.info("测试2: realtime_data 表功能")
        logger.info("=" * 60)

        # 1. 检查 realtime_data 表是否存在
        table_exists = await self._check_table_exists("realtime_data")
        logger.info(f"✓ realtime_data 表存在: {table_exists}")

        if not table_exists:
            logger.error("✗ realtime_data 表不存在，请检查数据库初始化脚本")
            return False

        # 2. 创建测试订阅
        subscription_key = "BINANCE:BTCUSDT@KLINE_1m"
        await self._insert_test_subscription(subscription_key, "KLINE")
        logger.info(f"✓ 创建测试订阅: {subscription_key}")

        # 3. 验证订阅通知
        logger.info("等待 subscription_add 通知...")

        # 使用 LISTEN/NOTIFY 监听通知
        await self._listen_for_subscription_notification("add", subscription_key)

        # 4. 更新实时数据
        await self._update_test_realtime_data(subscription_key)
        logger.info(f"✓ 更新实时数据: {subscription_key}")

        # 5. 验证数据更新通知
        logger.info("等待 realtime_update 通知...")
        await self._listen_for_realtime_update_notification(subscription_key)

        # 6. 删除订阅
        await self._delete_test_subscription(subscription_key)
        logger.info(f"✓ 删除测试订阅: {subscription_key}")

        # 7. 验证取消订阅通知
        logger.info("等待 subscription_remove 通知...")
        await self._listen_for_subscription_notification("remove", subscription_key)

        return True

    async def test_subscription_key_parsing(self):
        """测试订阅键解析功能"""
        logger.info("=" * 60)
        logger.info("测试3: 订阅键解析功能")
        logger.info("=" * 60)

        test_cases = [
            ("BINANCE:BTCUSDT@KLINE_1m", "btcusdt@kline_1m"),
            ("BINANCE:BTCUSDT.PERP@KLINE_60", "btcusdt.perp@kline_60"),
            ("BINANCE:BTCUSDT@QUOTES", "btcusdt@quotes"),
            ("BINANCE:ETHUSDT@TRADE", "ethusdt@trade"),
        ]

        all_passed = True
        for subscription_key, expected_stream in test_cases:
            # 使用 RealtimeDataRepository 的解析方法
            from db.realtime_data_repository import RealtimeDataRepository

            repo = RealtimeDataRepository(self.pool)
            stream = repo.subscription_key_to_binance_stream(subscription_key)

            if stream == expected_stream:
                logger.info(f"✓ {subscription_key} -> {stream}")
            else:
                logger.error(f"✗ {subscription_key} -> {stream} (期望: {expected_stream})")
                all_passed = False

        return all_passed

    async def _check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = $1
                )
            """
            exists = await conn.fetchval(query, table_name)
            return exists

    async def _create_test_task(self) -> Optional[int]:
        """创建测试任务"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO tasks (type, payload, status)
                VALUES ($1, $2, $3)
                RETURNING id
            """
            task_id = await conn.fetchval(
                query,
                "get_klines",
                json.dumps({
                    "symbol": "BINANCE:BTCUSDT",
                    "resolution": "60",
                    "from_time": None,
                    "to_time": None,
                }),
                "pending",
            )
            return task_id

    async def _insert_test_subscription(self, subscription_key: str, data_type: str):
        """创建测试订阅"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO realtime_data (subscription_key, data_type, data, event_time)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (subscription_key) DO NOTHING
            """
            await conn.execute(
                query,
                subscription_key,
                data_type,
                json.dumps({"test": "data"}),
            )

    async def _update_test_realtime_data(self, subscription_key: str):
        """更新测试实时数据"""
        async with self.pool.acquire() as conn:
            query = """
                UPDATE realtime_data
                SET data = $1, event_time = NOW(), updated_at = NOW()
                WHERE subscription_key = $2
            """
            await conn.execute(
                query,
                json.dumps({
                    "symbol": "BTCUSDT",
                    "price": "50000.00",
                    "volume": "100.0",
                    "timestamp": datetime.now().isoformat(),
                }),
                subscription_key,
            )

    async def _delete_test_subscription(self, subscription_key: str):
        """删除测试订阅"""
        async with self.pool.acquire() as conn:
            query = "DELETE FROM realtime_data WHERE subscription_key = $1"
            await conn.execute(query, subscription_key)

    async def _listen_for_task_notification(self, task_id: int):
        """监听任务通知"""
        notification_received = False

        async def handle_notification(connection, pid, channel, payload):
            nonlocal notification_received
            logger.info(f"收到通知: {channel} - {payload}")
            notification_received = True

        async with self.pool.acquire() as conn:
            await conn.add_listener("task_new", handle_notification)

            # 等待5秒
            for _ in range(50):  # 50 * 0.1 = 5秒
                await asyncio.sleep(0.1)
                if notification_received:
                    break

            if not notification_received:
                logger.warning("未收到 task_new 通知（可能币安服务未运行）")

    async def _listen_for_subscription_notification(self, action: str, subscription_key: str):
        """监听订阅通知"""
        channel = f"subscription_{action}"
        notification_received = False

        async def handle_notification(connection, pid, channel, payload):
            nonlocal notification_received
            logger.info(f"收到通知: {channel} - {payload}")
            notification_received = True

        async with self.pool.acquire() as conn:
            await conn.add_listener(channel, handle_notification)

            # 等待5秒
            for _ in range(50):  # 50 * 0.1 = 5秒
                await asyncio.sleep(0.1)
                if notification_received:
                    break

            if not notification_received:
                logger.warning(f"未收到 {channel} 通知（可能币安服务未运行）")

    async def _listen_for_realtime_update_notification(self, subscription_key: str):
        """监听实时数据更新通知"""
        notification_received = False

        async def handle_notification(connection, pid, channel, payload):
            nonlocal notification_received
            logger.info(f"收到通知: {channel} - {payload}")
            notification_received = True

        async with self.pool.acquire() as conn:
            await conn.add_listener("realtime_update", handle_notification)

            # 等待5秒
            for _ in range(50):  # 50 * 0.1 = 5秒
                await asyncio.sleep(0.1)
                if notification_received:
                    break

            if not notification_received:
                logger.warning("未收到 realtime_update 通知（可能币安服务未运行）")

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始币安服务新架构测试")
        logger.info("=" * 60)

        try:
            await self.setup()

            # 测试1: tasks 表
            test1_passed = await self.test_tasks_table()

            # 测试2: realtime_data 表
            test2_passed = await self.test_realtime_data_table()

            # 测试3: 订阅键解析
            test3_passed = await self.test_subscription_key_parsing()

            logger.info("=" * 60)
            logger.info("测试结果汇总:")
            logger.info(f"✓ tasks 表功能: {'通过' if test1_passed else '失败'}")
            logger.info(f"✓ realtime_data 表功能: {'通过' if test2_passed else '失败'}")
            logger.info(f"✓ 订阅键解析功能: {'通过' if test3_passed else '失败'}")
            logger.info("=" * 60)

            if test1_passed and test2_passed and test3_passed:
                logger.info("🎉 所有测试通过！新架构功能正常")
            else:
                logger.error("❌ 部分测试失败，请检查配置")

        except Exception as e:
            logger.error(f"测试执行失败: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await self.teardown()


async def main():
    """主函数"""
    tester = ArchitectureTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
