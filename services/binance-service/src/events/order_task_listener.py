"""
订单任务监听器

根据 04-trading-orders.md 设计：
- 监听频道：order_task_new
- 任务表：order_tasks
- 通知载荷格式与 TaskListener 相同

职责：
- 监听 order_task_new 频道（新订单任务通知）
- 解析任务载荷并分发到对应的处理器
- 支持的任务类型：order.create, order.cancel, order.query
"""

import asyncio
import json
import logging
from typing import Callable, Awaitable
from dataclasses import dataclass

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class OrderTaskCallback:
    """订单任务回调注册"""

    callback: Callable[..., Awaitable[None]]
    task_type: str  # order.create, order.cancel, order.query


class OrderTaskListener:
    """数据库订单任务监听器

    职责：
    - 监听 order_task_new 频道（新订单任务通知）
    - 解析任务载荷并分发到对应的处理器

    事件驱动流程：
    1. API网关 INSERT order_tasks 表
    2. 数据库触发器发送 order_task_new 通知
    3. 此监听器接收通知并分发处理

    使用方式：
        async def handle_order_create(payload: dict):
            print(f"创建订单: {payload}")

        listener = OrderTaskListener(pool)
        listener.register("order.create", handle_order_create)
        await listener.start()
    """

    # 监听频道
    CHANNEL = "order_task_new"

    def __init__(self, pool: asyncpg.Pool) -> None:
        """初始化监听器

        Args:
            pool: asyncpg 连接池
        """
        self._pool = pool
        self._callbacks: dict[str, list[OrderTaskCallback]] = {}
        self._running = False
        self._listener_task: asyncio.Task | None = None

    def register(
        self,
        task_type: str,
        callback: Callable[..., Awaitable[None]],
    ) -> None:
        """注册任务回调

        Args:
            task_type: 任务类型，如 "order.create", "order.cancel", "order.query"
            callback: 异步回调函数，接收任务载荷参数
        """
        if task_type not in self._callbacks:
            self._callbacks[task_type] = []
        self._callbacks[task_type].append(
            OrderTaskCallback(
                callback=callback,
                task_type=task_type,
            )
        )
        logger.info(f"已注册订单任务处理器: {task_type}")

    async def start(self) -> None:
        """开始监听数据库通知"""
        if self._running:
            logger.warning("订单任务监听器已在运行")
            return

        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info("订单任务监听器已启动")

    async def stop(self) -> None:
        """停止监听"""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        logger.info("订单任务监听器已停止")

    async def _listen_loop(self) -> None:
        """监听循环"""
        while self._running:
            try:
                async with self._pool.acquire() as conn:
                    # 监听订单任务通知频道
                    await conn.add_listener(self.CHANNEL, self._notify_handler)

                    # 保持连接活跃
                    while self._running:
                        await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"订单任务监听循环异常: {e}")
                await asyncio.sleep(5)  # 重试前等待

    def _notify_handler(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        """通知处理器（同步调用，需异步调度）"""
        asyncio.create_task(self._handle_notification(payload))

    async def _handle_notification(self, payload: str) -> None:
        """处理通知载荷

        通知格式（统一包装格式）：
        {
            "event_id": "...",
            "event_type": "order_task_new",
            "timestamp": "...",
            "data": {"id": 123, "type": "order.create", "payload": {...}, "status": "pending"}
        }
        """
        try:
            obj = json.loads(payload)

            # 支持两种格式：
            # 1. 统一包装格式：{event_id, event_type, timestamp, data: {...}}
            # 2. 直接格式：{id, type, payload, status}（向后兼容）
            if "data" in obj:
                # 统一包装格式
                data = obj["data"]
                task_id = data.get("id")
                task_type = data.get("type")
                task_payload = data.get("payload", {})
                logger.debug(
                    f"收到订单任务通知（包装格式）: {task_type} (task_id={task_id})"
                )
            else:
                # 直接格式（向后兼容）
                if "id" not in obj or "type" not in obj or "payload" not in obj:
                    logger.warning(f"通知载荷格式无效: {payload[:100]}")
                    return
                task_id = obj.get("id")
                task_type = obj.get("type")
                task_payload = obj.get("payload", {})
                logger.debug(
                    f"收到订单任务通知（直接格式）: {task_type} (task_id={task_id})"
                )

            # 验证 task_id 不为 None
            if task_id is None:
                logger.warning(f"通知载荷缺少任务ID: {payload[:100]}")
                return

            # 查找对应的处理器
            callbacks = self._callbacks.get(task_type, [])

            if not callbacks:
                logger.warning(f"未找到订单任务处理器: {task_type}")
                return

            # 构建任务载荷
            task_payload_obj = {
                "task_id": task_id,
                "type": task_type,
                "payload": task_payload,
            }

            # 执行所有匹配的回调
            for cb in callbacks:
                try:
                    await cb.callback(task_payload_obj)
                except Exception as e:
                    logger.error(f"执行订单任务回调失败: {e}")

        except json.JSONDecodeError:
            logger.error(f"无效的JSON载荷: {payload[:100]}")
        except Exception as e:
            logger.error(f"处理订单任务通知失败: {e}")
