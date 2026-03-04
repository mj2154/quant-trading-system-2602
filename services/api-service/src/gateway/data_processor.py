"""
数据处理器 - 统一数据处理中心

使用 PostgreSQL LISTEN/NOTIFY 机制监听数据库事件：
- 任务事件: task_completed, task_failed
- 实时数据: realtime_update
- 业务事件: signal_new, config.new/update/delete
- 告警配置: alert_config.new/update/delete

遵循 QUANT_TRADING_SYSTEM_ARCHITECTURE.md 设计。
作为 API 服务内部的统一数据处理中心，负责接收数据库通知并推送给客户端。
"""

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

import asyncpg

from ..converters import convert_binance_to_tv
from ..models.protocol.constants import PROTOCOL_VERSION
from ..models.protocol.ws_message import MessageError, MessageSuccess, MessageUpdate
from ..models.trading.kline_models import KlineBar, KlineBars
from .client_manager import ClientManager

if TYPE_CHECKING:
    from ..db.tasks_repository import TasksRepository
else:
    from ..db.tasks_repository import TasksRepository

logger = logging.getLogger(__name__)

# 任务类型映射：数据库类型 -> 前端类型
# 严格遵循07-websocket-protocol.md规范：使用具体数据类型
_TASK_TYPE_TO_RESPONSE_TYPE: dict[str, str] = {
    "get_klines": "KLINES_DATA",
    "get_quotes": "QUOTES_DATA",
    "get_server_time": "SERVER_TIME_DATA",
}


def _map_task_type_to_response_type(task_type: str) -> str:
    """映射任务类型为前端响应类型"""
    return _TASK_TYPE_TO_RESPONSE_TYPE.get(task_type, task_type)

# 任务事件频道列表
TASK_CHANNELS = [
    "task_completed",
    "task_failed",
]

# 订单任务事件频道列表
ORDER_TASK_CHANNELS = [
    "order_task_completed",
    "order_task_failed",
]

# 实时数据事件频道列表
REALTIME_CHANNELS = [
    "realtime_update",
]

# 业务事件频道列表
BUSINESS_CHANNELS = [
    "signal_new",
    "config.new",
    "config.update",
    "config.delete",
    # 告警配置事件频道
    "alert_config.new",
    "alert_config.update",
    "alert_config.delete",
]


class DataProcessor:
    """数据处理器 - 统一数据处理中心

    监听 PostgreSQL NOTIFY 事件并广播给相关客户端。
    作为 API 服务内部的统一数据处理中心，负责：
    - 监听任务完成通知 (task_completed, task_failed)
    - 监听实时数据更新 (realtime_update)
    - 监听业务事件 (signal_new, config.*, alert_config.*)
    - 处理任务结果并推送给客户端
    """

    def __init__(
        self,
        dsn: str,
        client_manager: ClientManager,
        tasks_repo: TasksRepository | None = None,
    ) -> None:
        """初始化通知监听器

        Args:
            dsn: 数据库连接字符串
            client_manager: 客户端管理器
            tasks_repo: 任务仓储（用于查询 klines_history 数据）
        """
        self._dsn = dsn
        self._client_manager = client_manager
        self._tasks_repo = tasks_repo
        self._connection: asyncpg.Connection | None = None
        self._listener_task: asyncio.Task | None = None
        self._running = False

    def set_tasks_repository(self, tasks_repo: TasksRepository) -> None:
        """设置任务仓储

        Args:
            tasks_repo: 任务仓储实例
        """
        self._tasks_repo = tasks_repo

    async def start(self) -> None:
        """启动监听器"""
        if self._running:
            return

        self._running = True

        # 创建独立连接用于监听
        self._connection = await asyncpg.connect(self._dsn)

        # 订阅任务事件频道
        for channel in TASK_CHANNELS:
            await self._connection.add_listener(
                channel, self._on_task_notification
            )
            logger.info(f"Subscribed to task channel: {channel}")

        # 订阅订单任务事件频道
        for channel in ORDER_TASK_CHANNELS:
            await self._connection.add_listener(
                channel, self._on_order_task_notification
            )
            logger.info(f"Subscribed to order task channel: {channel}")

        # 订阅实时数据事件频道
        for channel in REALTIME_CHANNELS:
            await self._connection.add_listener(
                channel, self._on_realtime_notification
            )
            logger.info(f"Subscribed to realtime channel: {channel}")

        # 订阅业务事件频道
        for channel in BUSINESS_CHANNELS:
            await self._connection.add_listener(
                channel, self._on_notification
            )
            logger.info(f"Subscribed to business channel: {channel}")

        # 启动监听任务
        self._listener_task = asyncio.create_task(self._listen_loop())

        logger.info("Notification listener started")

    async def stop(self) -> None:
        """停止监听器"""
        if not self._running:
            return

        self._running = False

        # 取消监听任务
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        # 移除监听器并关闭连接
        if self._connection:
            all_channels = BUSINESS_CHANNELS + TASK_CHANNELS + REALTIME_CHANNELS
            for channel in all_channels:
                try:
                    await self._connection.remove_listener(
                        channel, self._on_notification
                    )
                except Exception:
                    pass

            await self._connection.close()
            self._connection = None

        logger.info("Notification listener stopped")

    async def _on_notification(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        """处理业务事件通知回调

        Args:
            connection: 数据库连接
            pid: 后端进程 ID
            channel: 通知频道
            payload: 通知载荷（JSON 字符串）
        """
        try:
            data = json.loads(payload)
            event_type = data.get("event_type", channel)

            # signal_new 事件的 payload 有 data 包装，需要提取
            # 格式：{ event_type, timestamp, data: { alert_id, ... } }
            if channel in ("signal_new",):
                event_data = data.get("data", data)
            elif channel in ("config.new", "config.update", "config.delete"):
                event_data = data
            else:
                event_data = data.get("data", {})

            # 转换 UUID 为字符串（避免 JSON 序列化失败）
            event_data = self._convert_uuids_to_str(event_data)

            # 构建推送消息
            # 使用 MessageUpdate 模型确保符合协议规范
            subscription_key = self._get_subscription_key(event_type, event_data)
            message = MessageUpdate(
                type="UPDATE",
                protocol_version=PROTOCOL_VERSION,
                timestamp=self._timestamp_ms(),
                data={
                    "eventType": event_type,
                    "subscriptionKey": subscription_key,
                    "content": event_data,
                },
            ).model_dump(by_alias=True)

            logger.info(
                f"[Notification] channel={channel}, event_type={event_type}, "
                f"subscription_key={subscription_key}"
            )

            # 广播给订阅的客户端
            # 注意：signal_new 和 alert_config 事件使用下面的专用广播逻辑
            if channel not in ("signal_new", "alert_config.new", "alert_config.update", "alert_config.delete"):
                await self._client_manager.broadcast(
                    subscription_key, message
                )

            # 也尝试通配符匹配
            symbol = event_data.get("symbol", "")
            if symbol:
                exchange = event_data.get("exchange", "BINANCE")
                await self._client_manager.broadcast_pattern(
                    f"{exchange}:{symbol}",
                    message,
                    symbol,
                )

            # 对于信号和配置事件，广播到通用的策略频道
            if channel in ("signal_new", "config.new", "config.update", "config.delete"):
                await self._client_manager.broadcast(
                    "strategy:all",
                    message,
                )

            # 对于信号事件，广播到特定告警频道
            # 只广播到 SIGNAL:{alert_id}，不使用通配符
            if channel == "signal_new":
                # 获取 alert_id 用于精确广播
                alert_id = event_data.get("alert_id")

                # 广播到 SIGNAL:{alert_id}（用于订阅特定告警的客户端）
                if alert_id:
                    logger.info(f"[Broadcast] signal_new to SIGNAL:{alert_id}")
                    await self._client_manager.broadcast(
                        f"SIGNAL:{alert_id}",
                        message,
                    )
                else:
                    logger.warning("[Broadcast] signal_new has no alert_id, skipping broadcast")

            # 注意：alert_config 事件（alert_config.new/update/delete）不再广播到 SIGNAL: 频道
            # 前端通过订阅 SIGNAL:{alert_id} 来接收真正的信号 (signal_new)
            # 告警配置变更不需要推送到前端，前端会通过 CRUD 操作的响应更新本地状态

            logger.debug(
                f"Broadcasted business notification: channel={channel}, "
                f"event_type={event_type}"
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse notification payload: {e}")
        except Exception as e:
            logger.exception(f"Error handling notification: {e}")

    async def _on_task_notification(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        """处理任务完成/失败通知回调

        统一数据处理中心核心方法，负责处理任务完成通知。

        Args:
            connection: 数据库连接
            pid: 后端进程 ID
            channel: 通知频道 (task_completed 或 task_failed)
            payload: 通知载荷（JSON 字符串）

        数据库通知采用统一包装格式：
        {
            "event_id": "...",
            "event_type": "task_completed" 或 "task_failed",
            "timestamp": "...",
            "data": {
                "id": 123,
                "type": "get_quotes",
                "payload": {...},
                "result": {...},
                "status": "completed" 或 "failed",
                "updated_at": "..."
            }
        }
        """
        try:
            raw_data = json.loads(payload)

            # 统一包装格式：{event_id, event_type, timestamp, data: {...}}
            # 解析 data 字段获取任务信息
            data = raw_data.get("data", {})

            task_id = data.get("id")
            task_type = data.get("type")
            status = data.get("status")

            if not task_id:
                logger.warning(f"通知中缺少 task_id: {payload}")
                return

            logger.debug(
                f"收到任务通知: channel={channel}, task_id={task_id}, "
                f"task_type={task_type}, status={status}"
            )

            # 系统内部任务不需要客户端关联，跳过处理
            if task_type and task_type.startswith("system."):
                logger.debug(f"系统任务 {task_id} ({task_type}) 完成，无需客户端推送")
                return

            # 获取任务对应的客户端
            client_id = self._client_manager.get_client_by_task(task_id)
            if not client_id:
                # 可能是超时自动清理的映射，跳过处理
                logger.debug(f"未找到任务 {task_id} 对应的客户端，可能已超时")
                return

            # 取消注册任务映射
            self._client_manager.unregister_task(task_id)

            # 提取 payload 和 result（通知已包含，无需再查数据库）
            payload_data = data.get("payload", {})
            if isinstance(payload_data, str):
                payload_data = json.loads(payload_data)

            result = data.get("result")
            # 从通知的顶层 data 字段提取 request_id（已从 payload 提升到顶层）
            request_id = data.get("request_id")

            # 根据任务类型处理
            if task_type == "get_klines":
                # get_klines 的 result 为空，需查询 klines_history 表
                await self._handle_klines_result(client_id, task_id, payload_data, request_id)
            elif task_type in ("get_futures_account", "get_spot_account"):
                # 账户信息任务：result 为空，需查询 account_info 表
                await self._handle_account_info_result(client_id, task_id, task_type, payload_data, request_id)
            elif status == "failed":
                # 任务失败处理
                await self._handle_task_error(client_id, task_type, data, payload_data, request_id)
            else:
                # 其他任务成功处理（result 已包含在通知中）
                await self._handle_task_success(client_id, task_id, task_type, payload_data, result, request_id)

        except json.JSONDecodeError as e:
            logger.error(f"解析任务通知载荷失败: {e}, payload={payload}")
        except Exception as e:
            logger.exception(f"处理任务通知失败: {e}")

    async def _handle_klines_result(
        self, client_id: str, task_id: int, payload: dict[str, Any], request_id: str | None = None
    ) -> None:
        """处理 get_klines 任务结果

        查询 klines_history 表获取数据并推送给客户端。
        使用 KlineBars 和 MessageSuccess 模型确保数据格式符合 TradingView API 规范。

        Args:
            client_id: 客户端 ID
            task_id: 任务 ID
            payload: 通知中的 payload（包含请求参数）
            request_id: 请求 ID（从通知顶层获取）
        """
        try:
            symbol = payload.get("symbol", "")
            interval = payload.get("interval", "60")
            from_time = payload.get("from_time")
            to_time = payload.get("to_time")
            # request_id 从方法参数获取（通知顶层）

            if not all([symbol, interval, from_time, to_time]):
                logger.error(f"任务 {task_id} payload 不完整: {payload}")
                await self._send_error_to_client(
                    client_id, "INVALID_PAYLOAD", "Invalid task payload"
                )
                return

            if not self._tasks_repo:
                logger.error("任务仓储未设置，无法查询 klines_history")
                await self._send_error_to_client(
                    client_id, "REPO_NOT_SET", "Task repository not set"
                )
                return

            # 查询 klines_history 表获取数据
            klines_raw = await self._tasks_repo.query_klines_range(
                symbol=symbol,
                interval=interval,
                from_time=from_time,
                to_time=to_time,
            )

            # 转换数据格式为 KlineBar 列表
            bars_list = [
                KlineBar(
                    time=k.get("time", 0),
                    open=float(k.get("open", 0)),
                    high=float(k.get("high", 0)),
                    low=float(k.get("low", 0)),
                    close=float(k.get("close", 0)),
                    volume=float(k.get("volume", 0)),
                )
                for k in klines_raw
            ]

            # 使用 KlineBars 模型
            kline_data = KlineBars(
                symbol=symbol,
                interval=interval,
                bars=bars_list,
                count=len(bars_list),
                no_data=len(bars_list) == 0,
            )

            # 构建响应
            # 严格遵循07-websocket-protocol.md规范：使用具体数据类型
            kline_data_dict = kline_data.model_dump()
            kline_data_dict["type"] = "klines"
            response = MessageSuccess(
                type="KLINES_DATA",  # 遵循07-websocket-protocol.md规范
                request_id=request_id,
                protocol_version=PROTOCOL_VERSION,
                timestamp=self._timestamp_ms(),
                data=kline_data_dict,
            )

            success = await self._client_manager.send(
                client_id,
                response.model_dump(by_alias=True)
            )
            if success:
                logger.info(
                    f"已推送 klines 数据给客户端 {client_id}: "
                    f"{symbol} {interval} 共 {len(bars_list)} 条"
                )
            else:
                logger.warning(f"推送 klines 数据失败: client={client_id}")

        except Exception as e:
            logger.exception(f"处理 klines 结果失败: {e}")
            await self._send_error_to_client(
                client_id, "PROCESSING_ERROR", str(e)
            )

    async def _handle_account_info_result(
        self, client_id: str, task_id: int, task_type: str, payload: dict[str, Any], request_id: str | None = None
    ) -> None:
        """处理账户信息任务结果

        查询 account_info 表获取数据并推送给客户端。

        Args:
            client_id: 客户端 ID
            task_id: 任务 ID
            task_type: 任务类型 (get_futures_account / get_spot_account)
            payload: 通知中的 payload
            request_id: 请求 ID（从通知顶层获取）
        """
        try:
            # request_id 从方法参数获取（通知顶层）

            if not self._tasks_repo:
                logger.error("任务仓储未设置，无法查询 account_info")
                await self._send_error_to_client(
                    client_id, "REPO_NOT_SET", "Task repository not set"
                )
                return

            # 根据任务类型确定账户类型
            account_type = "FUTURES" if task_type == "get_futures_account" else "SPOT"

            # 查询 account_info 表获取数据
            account_info = await self._tasks_repo.get_account_info(account_type)

            if not account_info:
                logger.error(f"账户信息不存在: account_type={account_type}")
                await self._send_error_to_client(
                    client_id, "ACCOUNT_INFO_NOT_FOUND", f"Account info not found: {account_type}"
                )
                return

            # 构建响应 - 使用 content 字段符合文档规范
            task_data = {
                "type": task_type.replace("get_", "") + "s",  # get_futures_account -> futures_account
                "content": account_info.get("data"),
                "update_time": account_info.get("update_time"),
            }

            # 使用 MessageSuccess 模型构建响应
            # 严格遵循07-websocket-protocol.md规范：使用具体数据类型
            response = MessageSuccess(
                type="ACCOUNT_DATA",  # 遵循07-websocket-protocol.md规范
                request_id=request_id,
                protocol_version=PROTOCOL_VERSION,
                timestamp=self._timestamp_ms(),
                data=task_data,
            )

            response_dict = response.model_dump(by_alias=True)
            success = await self._client_manager.send(client_id, response_dict)
            if success:
                logger.info(
                    f"已推送账户信息给客户端 {client_id}: "
                    f"account_type={account_type}"
                )
            else:
                logger.warning(f"推送账户信息失败: client={client_id}")

        except Exception as e:
            logger.exception(f"处理账户信息结果失败: {e}")
            await self._send_error_to_client(
                client_id, "PROCESSING_ERROR", str(e)
            )

    async def _handle_task_success(
        self, client_id: str, task_id: int, task_type: str, payload: dict[str, Any], result: dict[str, Any], request_id: str | None = None
    ) -> None:
        """处理任务成功结果

        Args:
            client_id: 客户端 ID
            task_id: 任务 ID
            task_type: 任务类型
            payload: 通知中的 payload
            result: 通知中的任务结果
            request_id: 请求 ID（从通知顶层获取）
        """
        try:
            # request_id 从方法参数获取（通知顶层）
            response_type = _map_task_type_to_response_type(task_type)

            # 根据任务类型构建 data
            if task_type == "get_quotes":
                task_data = {
                    "type": response_type,
                    "quotes": result.get("quotes", []) if result else [],
                    "count": result.get("count", 0) if result else 0,
                }
            else:
                task_data = {
                    "type": response_type,
                }
                if result:
                    for key, value in result.items():
                        if key not in ["type", "taskType"]:
                            task_data[key] = value

            # 使用 MessageSuccess 模型构建响应
            # 严格遵循07-websocket-protocol.md规范：使用具体数据类型
            response = MessageSuccess(
                type=response_type,  # 使用映射后的具体数据类型（如 KLINES_DATA）
                request_id=request_id,
                protocol_version=PROTOCOL_VERSION,
                timestamp=self._timestamp_ms(),
                data=task_data,
            )

            success = await self._client_manager.send(client_id, response.model_dump(by_alias=True))
            if success:
                logger.info(
                    f"已推送任务结果给客户端 {client_id}: "
                    f"task_type={task_type}, task_id={task_id}"
                )

        except Exception as e:
            logger.exception(f"推送任务结果失败: {e}")
            await self._send_error_to_client(
                client_id, "RESULT_ERROR", str(e)
            )

    async def _on_order_task_notification(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        """处理订单任务完成/失败通知回调

        监听 order_task_completed 和 order_task_failed 通知，
        通过 task_id 查找客户端，将订单结果推送给相关客户端。

        Args:
            connection: 数据库连接
            pid: 后端进程 ID
            channel: 通知频道 (order_task_completed 或 order_task_failed)
            payload: 通知载荷（JSON 字符串）

        数据库通知格式（已更新）：
        {
            "event_id": "...",
            "event_type": "order_task_completed" 或 "order_task_failed",
            "timestamp": "...",
            "data": {
                "id": 123,
                "type": "order.create",
                "request_id": "req_xxx",
                "payload": {...},
                "result": {...},
                "status": "completed" 或 "failed",
                "updated_at": "..."
            }
        }
        """
        try:
            raw_data = json.loads(payload)

            # 解析 data 字段获取任务信息
            data = raw_data.get("data", {})

            task_id = data.get("id")
            task_type = data.get("type")
            request_id = data.get("request_id")  # 新的顶层字段
            status = data.get("status")

            if not task_id:
                logger.warning(f"订单任务通知中缺少 task_id: {payload}")
                return

            logger.debug(
                f"收到订单任务通知: channel={channel}, task_id={task_id}, "
                f"task_type={task_type}, request_id={request_id}, status={status}"
            )

            # 通过 task_id 查找客户端（TaskRouter 创建任务时已注册）
            client_id = self._client_manager.get_client_by_task(task_id)
            if not client_id:
                logger.debug(f"未找到订单任务 {task_id} 对应的客户端，跳过推送")
                return

            # 取消注册任务映射
            self._client_manager.unregister_task(task_id)

            # 提取结果数据
            payload_data = data.get("payload", {})
            if isinstance(payload_data, str):
                payload_data = json.loads(payload_data)

            result = data.get("result")

            # 构建响应消息 - 使用模型确保符合协议规范
            if status == "completed":
                # 订单创建成功
                message = MessageSuccess(
                    type="ORDER_DATA",
                    request_id=request_id,
                    protocol_version=PROTOCOL_VERSION,
                    timestamp=self._timestamp_ms(),
                    data={
                        "type": "order",
                        "status": "COMPLETED",
                        "taskId": task_id,
                        "result": result,
                        "payload": payload_data,
                    },
                ).model_dump(by_alias=True)
            else:
                # 订单失败
                error_message = result.get("error", "Unknown error") if isinstance(result, dict) else str(result)
                message = MessageError(
                    type="ERROR",
                    request_id=request_id,
                    protocol_version=PROTOCOL_VERSION,
                    timestamp=self._timestamp_ms(),
                    data={
                        "errorCode": "ORDER_FAILED",
                        "errorMessage": f"Order failed: {error_message}",
                    },
                ).model_dump(by_alias=True)

            # 发送给特定客户端（通过 task_id 找到的客户端）
            await self._client_manager.send(client_id, message)
            logger.info(f"已推送订单任务通知: task_id={task_id}, request_id={request_id}, status={status}")

        except json.JSONDecodeError as e:
            logger.error(f"解析订单任务通知载荷失败: {e}, payload={payload}")
        except Exception as e:
            logger.exception(f"处理订单任务通知失败: {e}")

    async def _handle_task_error(
        self, client_id: str, task_type: str, data: dict[str, Any], payload: dict[str, Any], request_id: str | None = None
    ) -> None:
        """处理任务错误结果

        Args:
            client_id: 客户端 ID
            task_type: 任务类型
            data: 通知数据
            payload: 通知中的 payload
            request_id: 请求 ID（从通知顶层获取）
        """
        _task_id = data.get("id")  # 保留以备将来使用
        # request_id 从方法参数获取（通知顶层）

        result = data.get("result")
        error_message = result if isinstance(result, str) else result.get("error", "Unknown error") if result else "Unknown error"

        # 严格遵循07-websocket-protocol.md规范：使用模型确保符合协议
        message = MessageError(
            type="ERROR",
            request_id=request_id or "",
            protocol_version=PROTOCOL_VERSION,
            timestamp=self._timestamp_ms(),
            data={
                "errorCode": "TASK_FAILED",
                "errorMessage": f"Task failed: {error_message}",
            },
        ).model_dump(by_alias=True)

        await self._client_manager.send(client_id, message)
        logger.info(f"已发送任务失败通知给客户端 {client_id}: {error_message}")

    async def _send_error_to_client(
        self, client_id: str, error_code: str, error_message: str
    ) -> None:
        """发送错误消息给客户端

        严格遵循07-websocket-protocol.md规范：
        - type 字段值为 "ERROR"

        Args:
            client_id: 客户端 ID
            error_code: 错误代码
            error_message: 错误消息
        """
        # 使用 MessageError 模型确保符合协议规范
        message = MessageError(
            type="ERROR",
            request_id="",
            protocol_version=PROTOCOL_VERSION,
            timestamp=self._timestamp_ms(),
            data={
                "errorCode": error_code,
                "errorMessage": error_message,
            },
        ).model_dump(by_alias=True)

        await self._client_manager.send(client_id, message)

    async def _on_realtime_notification(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        """处理实时数据更新通知回调

        Args:
            connection: 数据库连接
            pid: 后端进程 ID
            channel: 通知频道
            payload: 通知载荷（JSON 字符串）
        """
        try:
            data = json.loads(payload)
            event_data = data.get("data", {})
            subscription_key = event_data.get("subscription_key")
            data_type = event_data.get("data_type")
            realtime_data = event_data.get("data")

            logger.debug(
                f"收到实时数据更新: subscription_key={subscription_key}, "
                f"data_type={data_type}"
            )

            if not subscription_key:
                logger.warning(f"通知中缺少 subscription_key: {payload}")
                return

            # 构建推送消息 - 遵循 TradingView 格式
            # 严格遵循07-websocket-protocol.md规范：使用type字段
            # 将币安格式转换为TV格式
            tv_content = convert_binance_to_tv(data_type, realtime_data)

            # 修复 QUOTES 的 symbol 问题：从 subscription_key 提取正确格式覆盖 n 字段
            # 因为 convert_quotes 使用的是币安原始数据中的 symbol（缺少 .PERP 后缀）
            if data_type == "QUOTES" and subscription_key and "n" in tv_content:
                from ..converters.subscription import SubscriptionKeyParser
                parsed = SubscriptionKeyParser.parse(subscription_key)
                if parsed and parsed.symbol:
                    tv_content["n"] = f"BINANCE:{parsed.symbol}"

            # 使用 MessageUpdate 模型确保符合协议规范
            message = MessageUpdate(
                type="UPDATE",
                protocol_version=PROTOCOL_VERSION,
                timestamp=self._timestamp_ms(),
                data={
                    "subscriptionKey": subscription_key,
                    "content": tv_content,
                },
            ).model_dump(by_alias=True)

            # 调试：获取订阅的客户端
            clients: list[str] = self._client_manager._subscription_manager.get_subscribed_clients(subscription_key) if self._client_manager._subscription_manager else []
            logger.debug(f"[DEBUG] 订阅 {subscription_key} 的客户端: {clients}")

            # 广播给订阅的客户端
            await self._client_manager.broadcast(subscription_key, message)
            logger.debug(f"广播实时数据完成: {subscription_key}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse realtime notification payload: {e}")
        except Exception as e:
            logger.exception(f"Error handling realtime notification: {e}")

    async def _listen_loop(self) -> None:
        """监听循环

        保持连接活跃，处理通知。
        """
        while self._running:
            try:
                # 等待通知（add_listener 会自动处理）
                await asyncio.sleep(3600)  # 每小时唤醒一次保持活跃
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Listen loop error: {e}")
                await asyncio.sleep(5)  # 错误后等待重试

    def _get_subscription_key(
        self, event_type: str, event_data: dict[str, Any]
    ) -> str:
        """生成订阅键

        Args:
            event_type: 事件类型
            event_data: 事件数据

        Returns:
            订阅键字符串
        """
        symbol = event_data.get("symbol", "")
        interval = event_data.get("interval", "")

        if event_type.startswith("kline"):
            return f"{symbol}_{interval}"
        elif event_type == "signal_new":
            # signal_new 事件使用 SIGNAL:{alert_id} 格式
            # 与广播频道保持一致，以便前端订阅匹配
            alert_id = event_data.get("alert_id")
            if alert_id:
                return f"SIGNAL:{alert_id}"
            return "SIGNAL:unknown"
        elif event_type.startswith("alert_config"):
            # alert_config 事件使用 SIGNAL:{alert_id} 格式
            alert_id = event_data.get("id")
            if alert_id:
                # Convert UUID to string if needed
                alert_id_str = str(alert_id)
                return f"SIGNAL:{alert_id_str}"
            return "SIGNAL:unknown"
        elif event_type.startswith("config."):
            # config.new, config.update, config.delete
            return f"strategy:{event_type}"
        else:
            return f"{event_type}"

    def _convert_uuids_to_str(self, data: dict[str, Any]) -> dict[str, Any]:
        """递归转换字典中的 UUID 对象为字符串

        Args:
            data: 包含 UUID 的字典

        Returns:
            UUID 转换为字符串后的字典
        """
        if not isinstance(data, dict):
            return data

        result = {}
        for key, value in data.items():
            if isinstance(value, UUID):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = self._convert_uuids_to_str(value)
            elif isinstance(value, list):
                result[key] = [
                    self._convert_uuids_to_str(item) if isinstance(item, dict) else str(item) if isinstance(item, UUID) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _timestamp_ms(self) -> int:
        """获取当前时间戳（毫秒）"""
        import time
        return int(time.time() * 1000)

