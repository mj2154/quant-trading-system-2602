"""
数据库任务监听器

根据 QUANT_TRADING_SYSTEM_ARCHITECTURE.md 设计：
- 监听频道：task.new（带点号）
- 任务表：tasks
- 通知载荷（统一包装格式）：
  {
      "event_id": "...",
      "event_type": "task.new",
      "timestamp": "...",
      "data": {"id": 123, "type": "get_klines", "payload": {...}, "status": "pending"}
  }
- 任务类型：get_klines, get_server_time, get_quotes

事件驱动流程：
1. API网关 INSERT tasks 表 → 触发 task.new 通知
2. 币安服务监听 task.new 通知
3. 币安服务处理任务并 UPDATE tasks.result → 触发 task_completed 通知

参考设计文档：
- Section 2.1: tasks 任务表
- Section 2.1.1: 任务通知格式
- Section 5.3: 一次性请求详细流程
"""

import asyncio
import json
import logging
from typing import Callable, Awaitable
from dataclasses import dataclass

import asyncpg

from .notification import TaskPayload

logger = logging.getLogger(__name__)


@dataclass
class TaskCallback:
    """任务回调注册"""

    callback: Callable[..., Awaitable[None]]
    task_type: str  # 任务类型或 action，如 "subscribe_kline" 或 "tv.subscribe_kline"


class TaskListener:
    """数据库任务监听器

    职责：
    - 监听 task.new 频道（新任务通知）
    - 解析任务载荷并分发到对应的处理器
    - 仅支持新任务格式（get_klines, get_server_time, get_quotes）

    事件驱动流程：
    1. API网关 INSERT tasks 表
    2. 数据库触发器发送 task.new 通知
    3. 此监听器接收通知并分发处理

    使用方式：
        async def handle_get_klines(payload: TaskPayload):
            print(f"获取K线: {payload.symbol} {payload.interval}")

        listener = TaskListener(pool)
        listener.register("get_klines", handle_get_klines)
        await listener.start()
    """

    # 监听频道：task.new（带点号，与数据库触发器一致）
    CHANNEL = "task.new"

    def __init__(self, pool: asyncpg.Pool) -> None:
        """初始化监听器

        Args:
            pool: asyncpg 连接池
        """
        self._pool = pool
        self._callbacks: dict[str, list[TaskCallback]] = {}
        self._running = False
        self._listener_task: asyncio.Task | None = None

    def register(
        self,
        task_type: str,
        callback: Callable[..., Awaitable[None]],
    ) -> None:
        """注册任务回调

        Args:
            task_type: 任务类型，如 "subscribe_kline" 或 "tv.subscribe_kline"
            callback: 异步回调函数，接收 TaskPayload 参数
        """
        if task_type not in self._callbacks:
            self._callbacks[task_type] = []
        self._callbacks[task_type].append(
            TaskCallback(
                callback=callback,
                task_type=task_type,
            )
        )
        logger.info(f"已注册任务处理器: {task_type}")

    async def start(self) -> None:
        """开始监听数据库通知"""
        if self._running:
            logger.warning("任务监听器已在运行")
            return

        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info("数据库任务监听器已启动")

    async def stop(self) -> None:
        """停止监听"""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        logger.info("数据库任务监听器已停止")

    async def _listen_loop(self) -> None:
        """监听循环"""
        while self._running:
            try:
                async with self._pool.acquire() as conn:
                    # 监听任务通知频道
                    await conn.add_listener(self.CHANNEL, self._notify_handler)

                    # 保持连接活跃
                    while self._running:
                        await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监听循环异常: {e}")
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
            "event_type": "task.new",
            "timestamp": "...",
            "data": {"id": 123, "type": "get_klines", "payload": {...}, "status": "pending"}
        }

        支持的任务类型：
        - get_klines: 获取K线历史数据
        - get_server_time: 获取服务器时间
        - get_quotes: 获取实时报价
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
                    f"收到任务通知（包装格式）: {task_type} (task_id={task_id})"
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
                    f"收到任务通知（直接格式）: {task_type} (task_id={task_id})"
                )

            # 查找对应的处理器
            callbacks = self._callbacks.get(task_type, [])

            if not callbacks:
                logger.warning(f"未找到任务处理器: {task_type}")
                return

            # 执行所有匹配的回调
            for cb in callbacks:
                try:
                    # 创建 TaskPayload 兼容对象
                    payload_obj = TaskPayload(
                        task_type=task_type,
                        symbol=task_payload.get("symbol", ""),
                        interval=task_payload.get("interval", ""),  # 使用 interval 字段
                        task_id=task_id,
                        payload=json.dumps(task_payload),
                    )
                    await cb.callback(payload_obj)
                except Exception as e:
                    logger.error(f"执行任务回调失败: {e}")

        except json.JSONDecodeError:
            logger.error(f"无效的JSON载荷: {payload[:100]}")
        except Exception as e:
            logger.error(f"处理通知失败: {e}")
