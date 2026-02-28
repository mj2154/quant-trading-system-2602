"""
订阅管理器 - 适配 realtime_data 表

职责：
- 管理内存字典：subscription_key -> {client_ids}
- 维护数据库 realtime_data 表
- 判断何时新增/删除订阅键
- 发送通知给币安服务

设计要点：
- 内存字典用于快速判断客户端订阅状态
- 数据库表用于持久化和币安服务恢复
- API网关根据内存字典判断是否操作数据库
- 使用 RealtimeDataRepository 进行数据库操作

遵循 SUBSCRIPTION_AND_REALTIME_DATA.md 设计：
- INSERT realtime_data → pg_notify('subscription.add')
- DELETE realtime_data → pg_notify('subscription.remove')
- TRUNCATE realtime_data → pg_notify('subscription.clean')

重要：SIGNAL:* 等告警信号订阅不应存入 realtime_data 表
（它们只用于 API 网关内部的客户端广播，不应转发给币安服务）
"""

import asyncio
import logging
from typing import Optional

import asyncpg

from ..db.realtime_data_repository import RealtimeDataRepository

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """订阅管理器 - 基于 realtime_data 表"""

    SUBSCRIBER_ID = "api-service"  # 订阅源标识，用于区分不同服务的订阅

    # 信号订阅格式：SIGNAL:* 或 SIGNAL:{alert_id}
    # 这些订阅只用于 API 网关内部的客户端广播，不应存入 realtime_data 表
    SIGNAL_SUBSCRIPTION_PREFIX = "SIGNAL:"

    def __init__(self, pool: asyncpg.Pool) -> None:
        """初始化订阅管理器

        Args:
            pool: asyncpg 连接池
        """
        self._pool = pool
        self._repository = RealtimeDataRepository(pool)
        self._lock = asyncio.Lock()

        # 内存字典：subscription_key -> {client_id, ...}
        # 用于快速判断有多少客户端在订阅某个键
        self._subscriptions: dict[str, set[str]] = {}

        # 内存集合：记录哪些订阅键已在数据库中
        # 用于快速判断是否需要 INSERT
        self._db_keys: set[str] = set()

    async def start(self) -> None:
        """启动管理器"""
        logger.info("订阅管理器启动")
        # 不从数据库加载，因为重启后表会被清空
        # 前端重连后会自动重新订阅

    async def stop(self) -> None:
        """停止管理器"""
        logger.info("订阅管理器停止")

    # ========== 客户端订阅接口 ==========

    async def subscribe(
        self,
        client_id: str,
        subscription_key: str,
    ) -> bool:
        """客户端订阅

        Args:
            client_id: 客户端ID
            subscription_key: 订阅键（直接使用前端发送的格式，无需转换）

        Returns:
            是否触发了新的数据库INSERT
        """
        # 直接使用前端发送的原始key（遵循TV格式规范）
        # 格式: BINANCE:BTCUSDT@KLINE_1 (TV格式)
        key = subscription_key

        async with self._lock:
            # 1. 内存字典添加客户端
            if key not in self._subscriptions:
                self._subscriptions[key] = set()
            self._subscriptions[key].add(client_id)

            logger.debug(f"[订阅] 添加: key={key}, client={client_id}, total_clients={len(self._subscriptions[key])}")
            logger.debug(f"[订阅] 当前所有订阅键: {list(self._subscriptions.keys())}")

            # 2. 信号订阅只存在于内存中，不存入数据库
            # SIGNAL:* 等订阅只用于 API 网关内部的客户端广播
            if self.is_signal_subscription(key):
                logger.debug(f"[订阅] 信号订阅跳过数据库: {key}")
                return False

            # 3. 调用数据库添加订阅（使用 UPSERT 逻辑）
            # 注意：每次订阅都调用 add_subscription，因为可能需要追加 subscribers 数组
            # _db_keys 标记用于避免重复 INSERT，但不阻止 UPDATE
            if key not in self._db_keys:
                self._db_keys.add(key)

            # 从订阅键解析数据类型
            data_type = self._parse_data_type_from_key(key)
            result = await self._repository.add_subscription(key, data_type, self.SUBSCRIBER_ID)
            logger.debug(f"[订阅] 数据库操作结果: key={key}, result={result}")
            return result

    async def unsubscribe(
        self,
        client_id: str,
        subscription_key: str,
    ) -> bool:
        """客户端取消订阅

        Args:
            client_id: 客户端ID
            subscription_key: 订阅键（直接使用前端发送的格式，无需转换）

        Returns:
            是否触发了数据库DELETE
        """
        # 直接使用原始key
        key = subscription_key

        async with self._lock:
            # 1. 从内存字典移除客户端
            if key not in self._subscriptions:
                return False

            self._subscriptions[key].discard(client_id)

            # 2. 如果还有客户端订阅，不删除
            if self._subscriptions[key]:
                return False

            # 3. 清理空字典
            del self._subscriptions[key]

            # 4. 信号订阅只存在于内存中，不操作数据库
            if self.is_signal_subscription(key):
                logger.debug(f"[取消订阅] 信号订阅跳过数据库: {key}")
                return False

            # 5. 判断是否在数据库中
            if key not in self._db_keys:
                return False

            # 6. 从数据库删除（通过 Repository）
            self._db_keys.discard(key)
            return await self._repository.remove_subscription(key, self.SUBSCRIBER_ID)

    async def unsubscribe_all(self, client_id: str) -> list[str]:
        """客户端取消所有订阅

        Args:
            client_id: 客户端ID

        Returns:
            被删除的订阅键列表
        """
        deleted_keys = []

        async with self._lock:
            # 找出该客户端订阅的所有键
            keys_to_remove = []
            for sub_key, clients in self._subscriptions.items():
                if client_id in clients:
                    keys_to_remove.append(sub_key)

            # 逐个处理
            for sub_key in keys_to_remove:
                clients = self._subscriptions[sub_key]
                clients.discard(client_id)

                if not clients:
                    # 没有客户端了，删除
                    del self._subscriptions[sub_key]
                    if sub_key in self._db_keys:
                        self._db_keys.discard(sub_key)
                        deleted_keys.append(sub_key)
                        await self._repository.remove_subscription(sub_key, self.SUBSCRIBER_ID)

        return deleted_keys

    async def on_client_disconnect(self, client_id: str) -> None:
        """客户端断开连接处理

        等同于取消所有订阅。

        Args:
            client_id: 客户端ID
        """
        await self.unsubscribe_all(client_id)

    # ========== 广播接口 ==========

    async def broadcast(
        self,
        subscription_key: str,
        message: dict,
    ) -> None:
        """广播消息给订阅指定键的所有客户端

        Args:
            subscription_key: 订阅键
            message: 消息字典
        """
        clients = self._subscriptions.get(subscription_key, set())
        if not clients:
            return

        # TODO: 通过 ClientManager 发送消息
        # 这里只返回客户端列表，由调用方发送
        return list(clients)

    def get_subscribed_clients(self, subscription_key: str) -> list[str]:
        """获取订阅指定键的所有客户端

        Args:
            subscription_key: 订阅键

        Returns:
            客户端ID列表
        """
        return list(self._subscriptions.get(subscription_key, set()))

    def get_all_subscription_keys(self) -> list[str]:
        """获取所有订阅键

        Returns:
            订阅键列表
        """
        return list(self._subscriptions.keys())

    def get_subscription_count(self) -> int:
        """获取订阅总数（客户端-键对）"""
        return sum(len(clients) for clients in self._subscriptions.values())

    def get_key_count(self) -> int:
        """获取订阅键数量"""
        return len(self._subscriptions)

    # ========== 启动/关闭接口 ==========

    async def truncate_and_notify_clean(self) -> None:
        """清空所有订阅并发送clean通知

        API网关重启时调用：
        1. 清空内存字典
        2. 只删除 api-service 创建的订阅
        3. 发送clean_all通知
        """
        async with self._lock:
            # 清空内存
            self._subscriptions.clear()
            self._db_keys.clear()

        # 只删除 api-service 创建的订阅（保留其他服务创建的）
        removed_count = await self._repository.remove_api_service_subscriptions()

        # 发送 clean_all 通知
        await self._publish_clean_notification()

        logger.info(f"已清理 {removed_count} 条 api-service 订阅记录并发送 clean 通知")

    async def _publish_clean_notification(self) -> None:
        """发送清空订阅通知"""
        async with self._pool.acquire() as conn:
            await conn.execute('NOTIFY "subscription.clean", \'{"action": "clean_all"}\'')

    # ========== 辅助方法 ==========

    def _parse_data_type_from_key(self, subscription_key: str) -> str:
        """从订阅键解析数据类型

        Args:
            subscription_key: 订阅键，格式: {EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{RESOLUTION}]

        Returns:
            数据类型 (KLINE, QUOTES, TRADE)
        """
        # 订阅键格式: BINANCE:BTCUSDT@KLINE_1m
        # 或: BINANCE:BTCUSDT@QUOTES
        # 或: BINANCE:BTCUSDT@TRADE

        parts = subscription_key.split("@")
        if len(parts) < 2:
            return "UNKNOWN"

        data_part = parts[1]

        # 提取数据类型（KLINE_1m -> KLINE）
        if data_part.startswith("KLINE"):
            return "KLINE"
        elif data_part == "QUOTES":
            return "QUOTES"
        elif data_part == "TRADE":
            return "TRADE"
        else:
            return "UNKNOWN"

    def is_signal_subscription(self, subscription_key: str) -> bool:
        """检查是否是信号订阅

        信号订阅格式：SIGNAL:* 或 SIGNAL:{alert_id}
        这些订阅只用于 API 网关内部的客户端广播，不应存入 realtime_data 表

        Args:
            subscription_key: 订阅键

        Returns:
            是否是信号订阅
        """
        return subscription_key.startswith(self.SIGNAL_SUBSCRIPTION_PREFIX)

    # ========== 批量操作 ==========

    async def subscribe_batch(
        self,
        client_id: str,
        subscription_keys: list[str],
    ) -> int:
        """客户端批量订阅

        Args:
            client_id: 客户端ID
            subscription_keys: 订阅键列表

        Returns:
            触发数据库INSERT的次数
        """
        inserted_count = 0
        for key in subscription_keys:
            if await self.subscribe(client_id, key):
                inserted_count += 1
        return inserted_count

    async def unsubscribe_batch(
        self,
        client_id: str,
        subscription_keys: list[str],
    ) -> int:
        """客户端批量取消订阅

        Args:
            client_id: 客户端ID
            subscription_keys: 订阅键列表

        Returns:
            触发数据库DELETE的次数
        """
        deleted_count = 0
        for key in subscription_keys:
            if await self.unsubscribe(client_id, key):
                deleted_count += 1
        return deleted_count
