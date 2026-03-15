"""
WebSocket 客户端管理器 - 集成新任务机制

职责:
- 管理所有活跃的 WebSocket 连接
- 追踪请求与客户端的映射
- 追踪任务ID与客户端的映射
- 与 SubscriptionManager 集成处理订阅
- 支持任务结果的定向发送

遵循 SUBSCRIPTION_AND_REALTIME_DATA.md 设计：
- request_id → client_id 映射用于响应请求
- task_id → client_id 映射用于发送异步任务结果
"""

import asyncio
import logging
import uuid

from fastapi import WebSocket
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ClientManager:
    """WebSocket 客户端管理器"""

    def __init__(self) -> None:
        # client_id -> websocket
        self._clients: dict[str, WebSocket] = {}
        # request_id -> client_id
        self._requests: dict[str, str] = {}
        # task_id -> client_id（新增，用于异步任务结果）
        self._tasks: dict[int, str] = {}
        # 客户端连接锁
        self._lock = asyncio.Lock()
        # 订阅管理器（可选，用于断开时清理订阅）
        self._subscription_manager = None

    async def connect(self, websocket: WebSocket) -> str:
        """注册新的 WebSocket 客户端

        Args:
            websocket: FastAPI WebSocket 连接

        Returns:
            分配的 client_id
        """
        async with self._lock:
            client_id = f"client_{uuid.uuid4().hex[:12]}"
            self._clients[client_id] = websocket
            return client_id

    def set_subscription_manager(self, subscription_manager) -> None:
        """设置订阅管理器

        Args:
            subscription_manager: 订阅管理器实例
        """
        self._subscription_manager = subscription_manager

    async def disconnect(self, client_id: str) -> None:
        """注销 WebSocket 客户端

        清理所有相关请求映射，并通知订阅管理器清理订阅。

        Args:
            client_id: 客户端 ID
        """
        async with self._lock:
            # 清理连接
            self._clients.pop(client_id, None)

            # 清理请求映射
            self._requests = {
                req_id: cid
                for req_id, cid in self._requests.items()
                if cid != client_id
            }

        # 调用订阅管理器清理该客户端的所有订阅
        if self._subscription_manager:
            await self._subscription_manager.on_client_disconnect(client_id)

    def get_websocket(self, client_id: str) -> WebSocket | None:
        """获取客户端的 WebSocket 连接

        Args:
            client_id: 客户端 ID

        Returns:
            WebSocket 连接或 None
        """
        return self._clients.get(client_id)

    async def send(self, client_id: str, message: BaseModel) -> bool:
        """向指定客户端发送消息

        强制要求 message 为 Pydantic 模型，确保类型安全贯穿整个链路。

        Args:
            client_id: 客户端 ID
            message: 消息，必须是 Pydantic 模型

        Returns:
            发送是否成功
        """
        # 将模型转换为字典进行序列化
        message_dict = message.model_dump(by_alias=True)
        websocket = self.get_websocket(client_id)
        if websocket is None:
            logger.warning(f"ClientManager.send: 未找到客户端 {client_id}")
            return False

        try:
            # v2.1规范：type 在 data 内部
            msg_type = (
                message_dict.get("data", {}).get("type")
                if message_dict.get("data")
                else message_dict.get("type")
            )
            request_id = message_dict.get("requestId", "N/A")

            logger.debug(
                f"[ClientManager.send] 发送给 client_id={client_id}, requestId={request_id}, type={msg_type}"
            )
            # 使用 model_dump_json 确保正确序列化
            json_str = message.model_dump_json(by_alias=True, exclude_none=True)
            logger.debug(f"ClientManager.send: 完整消息: {json_str}")
            await websocket.send_text(json_str)
            logger.debug("ClientManager.send: 发送成功")
            return True
        except Exception as e:
            logger.warning(f"ClientManager.send: 发送失败 {client_id}: {e}")
            # 发送失败，标记客户端为断开
            await self.disconnect(client_id)
            return False

    async def broadcast(self, subscription_key: str, message: BaseModel) -> None:
        """广播消息给订阅指定键的所有客户端

        强制要求 message 为 Pydantic 模型，确保类型安全。

        支持通配符匹配：
        - 精确匹配：订阅 'SIGNAL:123' 接收发送到 'SIGNAL:123' 的消息
        - 前缀匹配：订阅 'SIGNAL:*' 接收发送到 'SIGNAL:xxx' 的消息
        - 通配符 '*' 匹配所有消息

        Args:
            subscription_key: 订阅键
            message: 消息，必须是 Pydantic 模型
        """
        if not self._subscription_manager:
            return

        clients = set()

        # 获取所有订阅键进行调试
        all_keys = self._subscription_manager.get_all_subscription_keys()
        logger.debug(f"[Broadcast] subscription_key={subscription_key}")
        logger.debug(f"[Broadcast] 所有订阅键: {all_keys}")

        # 1. 精确匹配
        exact_clients = self._subscription_manager.get_subscribed_clients(
            subscription_key
        )
        logger.debug(
            f"[Broadcast] 精确匹配 {subscription_key}: {len(exact_clients)} 客户端"
        )
        clients.update(exact_clients)

        # 2. 通配符匹配：检查 subscription_key 是否是订阅键的前缀
        # 例如：subscription_key="SIGNAL:019c..." 匹配订阅 "SIGNAL:*" 的客户端
        for key in all_keys:
            # 处理前缀通配符订阅，如 "SIGNAL:*" 匹配 "SIGNAL:xxx"
            if "*" in key:
                # 将 "SIGNAL:*" 转换为前缀 "SIGNAL:"
                wildcard_prefix = key.replace("*", "")
                if subscription_key.startswith(wildcard_prefix):
                    wildcard_clients = (
                        self._subscription_manager.get_subscribed_clients(key)
                    )
                    logger.debug(
                        f"[广播] 通配符匹配: {key} 匹配 {subscription_key}, 客户端数: {len(wildcard_clients)}"
                    )
                    clients.update(wildcard_clients)
            # 处理普通前缀匹配，如 "BINANCE:" 匹配 "BINANCE:BTCUSDT"
            elif key.endswith(":") and subscription_key.startswith(key):
                wildcard_clients = self._subscription_manager.get_subscribed_clients(
                    key
                )
                clients.update(wildcard_clients)

        # 3. 检查通配符订阅 "*" 匹配所有
        all_star_clients = self._subscription_manager.get_subscribed_clients("*")
        clients.update(all_star_clients)

        if not clients:
            logger.debug(f"[Broadcast] 没有客户端订阅 key={subscription_key}")
            return

        logger.debug(
            f"[Broadcast] Broadcasting to {len(clients)} clients for key: {subscription_key}"
        )

        # 并发发送，不等待完成
        tasks = [self.send(client_id, message) for client_id in clients]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_pattern(self, pattern: str, message: BaseModel, symbol: str) -> None:
        """按模式广播消息给匹配的订阅客户端

        强制要求 message 为 Pydantic 模型。

        支持通配符匹配，如 `BINANCE:*` 匹配所有 BINANCE 订阅。

        Args:
            pattern: 订阅键模式
            message: 消息，必须是 Pydantic 模型
            symbol: 消息相关的交易对
        """
        # 精确匹配
        await self.broadcast(pattern, message)

        # 通配符匹配 - 从订阅管理器获取所有键
        if ":" in pattern:
            prefix, _ = pattern.rsplit(":", 1)
            if prefix and self._subscription_manager:
                all_keys = self._subscription_manager.get_all_subscription_keys()
                exchange_clients: set[str] = set()
                for sub_key in all_keys:
                    if (
                        sub_key.startswith(prefix + ":")
                        and ":" in sub_key[len(prefix) + 1 :]
                    ):
                        clients = self._subscription_manager.get_subscribed_clients(
                            sub_key
                        )
                        exchange_clients.update(clients)

                for client_id in exchange_clients:
                    await self.send(client_id, message)

    def register_request(self, request_id: str, client_id: str) -> None:
        """注册请求 ID 与客户端的映射

        Args:
            request_id: 请求 ID
            client_id: 客户端 ID
        """
        self._requests[request_id] = client_id

    def get_client_by_request(self, request_id: str) -> str | None:
        """根据请求 ID 获取客户端 ID

        Args:
            request_id: 请求 ID

        Returns:
            客户端 ID 或 None
        """
        return self._requests.get(request_id)

    # ========== 任务映射管理 ==========

    def register_task(self, task_id: int, client_id: str) -> None:
        """注册任务ID与客户端的映射

        Args:
            task_id: 任务ID
            client_id: 客户端ID
        """
        self._tasks[task_id] = client_id

    def get_client_by_task(self, task_id: int) -> str | None:
        """根据任务ID获取客户端ID

        Args:
            task_id: 任务ID

        Returns:
            客户端ID或None
        """
        return self._tasks.get(task_id)

    def unregister_task(self, task_id: int) -> None:
        """取消注册任务ID

        Args:
            task_id: 任务ID
        """
        self._tasks.pop(task_id, None)

    def get_task_count(self) -> int:
        """获取任务总数

        Returns:
            任务数量
        """
        return len(self._tasks)

    def get_client_count(self) -> int:
        """获取客户端数量

        Returns:
            客户端数量
        """
        return len(self._clients)
