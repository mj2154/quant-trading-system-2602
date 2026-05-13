"""
任务路由器 - 支持新任务表机制

将客户端请求路由到相应的处理函数：
- 直接查询类型：config, search_symbols, resolve_symbol（API网关直接处理）
- 异步任务类型：get_klines, get_server_time, get_quotes（INSERT tasks表）
- 告警类型：create_alert_config, list_alert_configs, update_alert_config (包含启用/禁用), delete_alert_config, list_signals

遵循 SUBSCRIPTION_AND_REALTIME_DATA.md 设计：
- 异步任务通过 tasks 表触发通知
- 任务完成后通过 task_completed 通知返回结果

K线历史数据查询策略（重要）：
1. 先根据周期对齐时间（from_time, to_time）
2. 查询 klines_history 表，验证起始和结束两个时间点的数据
3. 如果任意一个不存在，创建异步任务去币安API获取
4. 如果两个都存在，直接从数据库返回数据（不走异步任务）
5. **只验证端点，不验证中间数据**（中间数据缺失不影响返回）
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

from ..db.alert_signal_repository import AlertConfigRepository
from ..db.exchange_info_repository import ExchangeInfoRepository
from ..db.order_tasks_repository import OrderTasksRepository
from ..db.strategy_metadata_repository import StrategyMetadataRepository
from ..db.strategy_signals_repository import StrategySignalsRepository
from ..db.tasks_repository import TasksRepository
from ..models.base import CamelCaseModel
from ..models.db.signal_models import (
    StrategyMetadataListResponse,
    StrategyMetadataResponse,
)
from ..models.protocol.constants import PROTOCOL_VERSION
from ..models.protocol.ws_message import (
    ErrorData,
    KlinesRequest,
    MessageError,
    MessageSuccess,
    QuotesRequest,
)
from ..models.protocol.ws_payload import (
    AckData,
    ConfigData,
    MetricsData,
    SearchSymbolsData,
    StrategyMetadataByTypeData,
    SubscribeData,
    SymbolType,
    SystemMetrics,
    UnsubscribeData,
)
from ..models.trading.kline_models import KlineBar, KlineBars
from ..models.trading.order_models import (
    CancelOrderRequest,
    FuturesCreateOrderRequest,
    FuturesModifyOrderRequest,
    GetOrderRequest,
    OpenOrdersResponseData,
    OrderCancelResponseData,
    OrderData,
    OrderListResponseData,
    SpotAmendOrderRequest,
    SpotCreateOrderRequest,
)
from ..protocol.messages import MessageAck
from ..utils.symbol import parse_semantic_symbol
from .alert_handler import AlertHandler
from .client_manager import ClientManager
from .subscription_manager import SubscriptionManager

logger = logging.getLogger(__name__)


class TaskRouter:
    """任务路由器 - 将客户端请求转换为任务"""

    def __init__(
        self,
        subscription_manager: SubscriptionManager,
        client_manager: ClientManager,
        task_repo: None = None,
    ) -> None:
        """初始化任务路由器

        Args:
            subscription_manager: 订阅管理器实例
            client_manager: 客户端管理器实例（用于任务-客户端映射）
        """
        self._task_repo = task_repo
        self._subscription_manager = subscription_manager
        self._client_manager = client_manager

        # 新任务仓储（基于 tasks 表）
        self._tasks_repo: TasksRepository | None = None

        # 订单任务仓储（基于 order_tasks 表）
        self._order_tasks_repo: OrderTasksRepository | None = None

        # 交易所信息仓储
        self._exchange_repo: ExchangeInfoRepository | None = None

        # 策略元数据仓储
        self._strategy_metadata_repo: StrategyMetadataRepository | None = None

        # 告警处理器
        self._alert_handler: AlertHandler | None = None

    def set_tasks_repository(self, tasks_repo: TasksRepository) -> None:
        """设置新任务仓储实例

        Args:
            tasks_repo: 新任务仓储实例（基于 tasks 表）
        """
        self._tasks_repo = tasks_repo

    def set_order_tasks_repository(
        self, order_tasks_repo: OrderTasksRepository
    ) -> None:
        """设置订单任务仓储实例

        Args:
            order_tasks_repo: 订单任务仓储实例（基于 order_tasks 表）
        """
        self._order_tasks_repo = order_tasks_repo
        logger.info("OrderTasksRepository set in TaskRouter")

    def set_exchange_info_repository(
        self, exchange_repo: ExchangeInfoRepository
    ) -> None:
        """设置交易所信息仓储实例

        Args:
            exchange_repo: 交易所信息仓储实例
        """
        self._exchange_repo = exchange_repo

    def set_strategy_metadata_repository(
        self, strategy_metadata_repo: StrategyMetadataRepository
    ) -> None:
        """设置策略元数据仓储实例

        Args:
            strategy_metadata_repo: 策略元数据仓储实例
        """
        self._strategy_metadata_repo = strategy_metadata_repo
        logger.info("StrategyMetadataRepository set in TaskRouter")

    def set_alert_repository(
        self,
        alert_repo: AlertConfigRepository,
        signals_repo: StrategySignalsRepository | None = None,
    ) -> None:
        """设置告警配置仓储实例

        Args:
            alert_repo: 告警配置仓储实例（操作 alert_configs 表）
            signals_repo: 可选，策略信号仓储实例（操作 strategy_signals 表）
        """
        self._alert_handler = AlertHandler(alert_repo, signals_repo)
        logger.info("AlertHandler initialized")

    @property
    def subscription_manager(self) -> SubscriptionManager:
        """获取订阅管理器实例"""
        return self._subscription_manager

    def _create_ack(self, request_id: str | None) -> MessageAck:
        """创建 ACK 确认响应（三阶段模式第一阶段）

        严格遵循 07-websocket-protocol.md 规范：
        - type 字段值为 "ACK"（在顶层）
        - data 为空对象 {}

        Args:
            request_id: 请求 ID（用于关联 ack 确认和最终响应）

        Returns:
            MessageAck 模型实例
        """
        import time as time_module

        return MessageAck(
            request_id=request_id or "",
            type="ACK",
            timestamp=int(time_module.time() * 1000),
            data=AckData(),
        )

    async def _send_ack_and_process(
        self, client_id: str, request_id: str | None, process_fn
    ) -> None:
        """发送 ACK 并异步处理请求（三阶段模式）

        先立即发送 ACK 确认，然后异步执行实际处理逻辑，
        处理完成后再次发送响应。

        严格遵循 07-websocket-protocol.md 规范：
        请求 → ack确认 → (处理) → success/error回应

        Args:
            client_id: 客户端 ID
            request_id: 请求 ID
            process_fn: 异步处理函数

        Returns:
            ACK 确认消息（第一阶段）
        """
        # 第一阶段：立即发送 ACK 确认
        ack_response = self._create_ack(request_id)
        await self._client_manager.send(client_id, ack_response)

        # 第二阶段：异步执行处理逻辑
        result = await process_fn()

        # 第三阶段：发送处理结果
        await self._client_manager.send(client_id, result)

        # 返回 None 表示响应已由内部发送
        return None

    async def handle(
        self, client_id: str, request: dict[str, Any]
    ) -> MessageSuccess | MessageError | None:
        """处理客户端请求（严格遵循07-websocket-protocol.md）

        协议格式：顶层type字段直接是具体操作类型（如GET_CONFIG, GET_KLINES等）

        三阶段模式（严格遵循协议要求）：
        1. 所有请求都先返回 ACK 确认
        2. 然后处理请求
        3. 最后返回结果

        Args:
            client_id: 客户端 ID
            request: 解析后的请求消息

        Returns:
            响应消息（返回 None 表示消息已由内部发送）
        """
        # 严格遵循07-websocket-protocol.md：type字段直接是操作类型
        msg_type = request.type
        data = request.data
        request_id = request.request_id

        logger.debug(
            f"handle: msg_type={msg_type}, request_id={request_id}"
        )

        # ========== 需要三阶段模式的请求类型 ==========
        # 严格遵循07-websocket-protocol.md：所有请求都先返回 ACK，确认后再处理

        # 配置请求 - 三阶段模式
        if msg_type == "GET_CONFIG":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = self._handle_get_config(request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        # 服务器时间 - 异步任务（已有三阶段模式）
        elif msg_type == "GET_SERVER_TIME":
            return await self._create_async_task(
                client_id=client_id,
                task_type="get_server_time",
                payload={},
                request_id=request_id,
            )

        # 指标请求 - 三阶段模式
        elif msg_type == "GET_METRICS":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = self._handle_get_metrics(request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        # K线历史数据查询 - 混合模式
        elif msg_type == "GET_KLINES":
            return await self._handle_get_klines(client_id, data, request_id)

        # 交易对搜索
        # 交易对搜索 - 三阶段模式
        elif msg_type == "GET_SEARCH_SYMBOLS":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_get_search_symbols(data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        # 交易对解析 - 三阶段模式
        elif msg_type == "GET_RESOLVE_SYMBOL":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_get_resolve_symbol(data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        # 报价数据 - 异步任务
        elif msg_type == "GET_QUOTES":
            # 使用 SnakeCaseModel 验证请求，自动将 camelCase 转换为 snake_case
            try:
                validated = QuotesRequest.model_validate(data)
                symbols = validated.symbols
            except Exception as e:
                return self._error_response(
                    error_code="INVALID_PARAMETERS",
                    error_message=f"Missing symbols parameter: {str(e)}",
                )

            if not symbols:
                return self._error_response(
                    error_code="INVALID_PARAMETERS",
                    error_message="Missing symbols parameter",
                )
            return await self._create_async_task(
                client_id=client_id,
                task_type="get_quotes",
                payload={"symbols": symbols},
                request_id=request_id,
            )

        # 账户信息请求
        elif msg_type == "GET_FUTURES_ACCOUNT":
            return await self._create_async_task(
                client_id=client_id,
                task_type="get_futures_account",
                payload={},
                request_id=request_id,
            )

        elif msg_type == "GET_SPOT_ACCOUNT":
            return await self._create_async_task(
                client_id=client_id,
                task_type="get_spot_account",
                payload={},
                request_id=request_id,
            )

        # ========== 订阅类型（严格遵循07-websocket-protocol.md：三阶段模式）==========
        # 订阅请求 - 三阶段模式
        elif msg_type == "SUBSCRIBE":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_subscribe(client_id, data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        # 取消订阅 - 三阶段模式
        elif msg_type == "UNSUBSCRIBE":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_unsubscribe(client_id, data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        # ========== 告警配置请求（严格遵循07-websocket-protocol.md：三阶段模式）==========
        # 告警配置请求 - 三阶段模式
        elif msg_type == "CREATE_ALERT_CONFIG":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_alert_request("create", data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        elif msg_type == "LIST_ALERT_CONFIGS":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_alert_request("list", data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        elif msg_type == "UPDATE_ALERT_CONFIG":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_alert_request("update", data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        elif msg_type == "DELETE_ALERT_CONFIG":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_alert_request("delete", data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        # 注意：启用/禁用告警已合并到 UPDATE_ALERT_CONFIG 中
        # 使用 UPDATE_ALERT_CONFIG 并在 data 中包含 isEnabled 字段

        elif msg_type == "LIST_SIGNALS":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_alert_request("list_signals", data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        elif msg_type == "GET_STRATEGY_METADATA":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_get_strategy_metadata(data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        elif msg_type == "GET_STRATEGY_METADATA_BY_TYPE":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_get_strategy_metadata_by_type(data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        # ========== 订单交易请求（严格遵循 07-websocket-protocol.md：三阶段模式）==========
        # 订单交易请求 - 三阶段模式
        # 注意：CREATE_ORDER 不在这里发送响应，而是由 _on_order_task_notification 通知处理后发送
        elif msg_type == "CREATE_ORDER":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：创建任务并注册映射（由 _on_order_task_notification 发送最终响应）
            await self._handle_create_order(client_id, data, request_id)
            # 不发送响应，等待币安服务处理完成后的通知
            return None

        elif msg_type == "GET_ORDER":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：创建任务并注册映射（由 _on_order_task_notification 发送最终响应）
            await self._handle_get_order(client_id, data, request_id)
            # 不发送响应，等待币安服务处理完成后的通知
            return None

        elif msg_type == "LIST_ORDERS":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_list_orders(client_id, data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        elif msg_type == "CANCEL_ORDER":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_cancel_order(client_id, data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        elif msg_type == "MODIFY_ORDER":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：创建任务并注册映射（由 _on_order_task_notification 发送最终响应）
            await self._handle_modify_order(client_id, data, request_id)
            # 不发送响应，等待币安服务处理完成后的通知
            return None

        elif msg_type == "GET_OPEN_ORDERS":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_get_open_orders(client_id, data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        # ========== 未知类型 ==========
        else:
            return self._error_response(
                error_code="UNKNOWN_TYPE",
                error_message=f"Unknown type: {msg_type}",
                request_id=request_id,
            )

    # ========== 直接查询处理方法（遵循07-websocket-protocol.md：顶层type是具体操作）==========

    def _handle_get_config(self, request_id: str | None) -> MessageSuccess:
        """处理 GET_CONFIG 请求

        Args:
            request_id: 请求 ID

        Returns:
            配置数据响应
        """
        # 使用 ConfigData 模型构建响应
        config_data = ConfigData(
            supports_search=True,
            supports_group_request=False,
            supports_marks=False,
            supports_timescale_marks=False,
            supports_time=True,
            symbols_types=[
                SymbolType(name="All types", value=""),
                SymbolType(name="Crypto", value="crypto"),
            ],
            currency_codes=["USDT", "BTC", "ETH", "BNB", "BUSD", "USDC", "FDUSD"],
            supported_resolutions=[
                "1",
                "5",
                "15",
                "60",
                "240",
                "1D",
                "1W",
                "1M",
            ],
        )
        return self._response(
            msg_type="CONFIG_DATA",
            request_id=request_id,
            data=config_data,
        )

    def _handle_get_metrics(self, request_id: str | None) -> MessageSuccess:
        """处理 GET_METRICS 请求

        Args:
            request_id: 请求 ID

        Returns:
            指标数据响应
        """
        pending_count = 0
        if self._tasks_repo:
            # 异步调用需要处理
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 在异步环境中，创建任务获取
                    pending_count = 0  # 暂不支持
                else:
                    pending_count = asyncio.run(self._tasks_repo.get_pending_count())
            except Exception:
                pass

        # 使用 MetricsData 模型构建响应
        metrics_data = MetricsData(
            type="metrics",
            metrics=SystemMetrics(
                pending_tasks=pending_count,
                connected_clients=0,
            ),
        )
        return self._response(
            msg_type="METRICS_DATA",
            request_id=request_id,
            data=metrics_data,
        )

    async def _handle_get_klines(
        self, client_id: str, data: dict[str, Any], request_id: str | None
    ) -> MessageSuccess:
        """处理 GET_KLINES 请求（严格遵循07-websocket-protocol.md：三阶段模式）

        协议要求：无论缓存是否命中，都必须先返回 ACK 确认。

        使用 KlinesRequest 模型验证数据，自动将 camelCase 转换为 snake_case。

        Args:
            client_id: 客户端 ID
            data: 请求数据
            request_id: 请求 ID

        Returns:
            None（响应已由内部发送）
        """
        # 使用 SnakeCaseModel 验证请求，自动将 camelCase 转换为 snake_case
        try:
            validated = KlinesRequest.model_validate(data)
            symbol = validated.symbol
            interval = validated.interval
            from_time = validated.from_time
            to_time = validated.to_time

            # 记录获取历史K线请求的详细信息（INFO级别，方便排查问题）
            from datetime import datetime, timezone, timedelta
            tz_cn = timezone(timedelta(hours=8))
            from_ts = datetime.fromtimestamp(from_time / 1000, tz=tz_cn).strftime("%Y-%m-%d %H:%M:%S") if from_time else "None"
            to_ts = datetime.fromtimestamp(to_time / 1000, tz=tz_cn).strftime("%Y-%m-%d %H:%M:%S") if to_time else "None"
            logger.info(
                f"[GET_KLINES] 收到获取K线请求: symbol={symbol}, interval={interval}, "
                f"from_time={from_time} ({from_ts}), to_time={to_time} ({to_ts})"
            )
        except Exception as e:
            # 参数错误，也需要先发送 ACK 再发送错误
            await self._client_manager.send(client_id, self._create_ack(request_id))
            error_resp = self._error_response(
                error_code="INVALID_PARAMETERS",
                error_message=f"Missing required parameters: {str(e)}",
            )
            await self._client_manager.send(client_id, error_resp)
            return None

        # 验证时间范围：from_time 必须小于 to_time
        if from_time >= to_time:
            # 参数错误，也需要先发送 ACK 再发送错误
            await self._client_manager.send(client_id, self._create_ack(request_id))
            error_resp = self._error_response(
                error_code="INVALID_PARAMETER",
                error_message="from_time must be less than to_time",
            )
            await self._client_manager.send(client_id, error_resp)
            return None

        # 对齐时间到 K 线开盘时间
        from_time_aligned = self._align_to_kline_open_time(from_time, interval)
        to_time_aligned = self._align_to_kline_open_time(to_time, interval)

        # 第一阶段：发送 ACK（严格遵循协议：无论缓存是否命中都先发送 ACK）
        await self._client_manager.send(client_id, self._create_ack(request_id))

        # 第二阶段：检查端点数据是否存在并处理
        if self._tasks_repo:
            endpoints = await self._tasks_repo.check_kline_endpoints_exist(
                symbol=symbol,
                interval=interval,
                from_time=from_time_aligned,
                to_time=to_time_aligned,
            )

            if endpoints["from_exists"] and endpoints["to_exists"]:
                logger.debug(
                    f"缓存命中（端点完整）: {symbol} {interval} "
                    f"({from_time_aligned} - {to_time_aligned})"
                )
                klines_raw = await self._tasks_repo.query_klines_range(
                    symbol=symbol,
                    interval=interval,
                    from_time=from_time_aligned,
                    to_time=to_time_aligned,
                )
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
                kline_data = KlineBars(
                    symbol=symbol,
                    interval=interval,
                    bars=bars_list,
                    count=len(bars_list),
                    no_data=len(bars_list) == 0,
                )
                result = self._response(
                    msg_type="KLINES_DATA",
                    request_id=request_id,
                    data=kline_data,
                )
                # 记录缓存命中时返回K线数据
                logger.info(
                    f"[GET_KLINES] 缓存命中返回K线: symbol={symbol}, interval={interval}, "
                    f"count={len(bars_list)}, from={from_time_aligned}, to={to_time_aligned}"
                )
            else:
                missing = []
                if not endpoints["from_exists"]:
                    missing.append("from_time")
                if not endpoints["to_exists"]:
                    missing.append("to_time")
                logger.debug(
                    f"缓存缺失（端点不完整）: {symbol} {interval} "
                    f"缺少: {', '.join(missing)}，创建异步任务"
                )
                # 缓存缺失时，创建异步任务获取数据
                logger.info(
                    f"[GET_KLINES] 缓存缺失，创建异步任务: symbol={symbol}, "
                    f"interval={interval}, from={from_time_aligned}, to={to_time_aligned}"
                )
                result = await self._create_async_task(
                    client_id=client_id,
                    task_type="get_klines",
                    payload={
                        "symbol": symbol,
                        "interval": interval,
                        "from_time": from_time_aligned,
                        "to_time": to_time_aligned,
                    },
                    store_result=False,
                    request_id=request_id,
                )
                # 异步任务已返回 ACK，这里只需要发送最终结果
                # 注意：异步任务返回的 MessageSuccess 实例会被忽略，因为第一阶段已发送
                # 检查 type 属性判断是否为 ACK
                if result.type == "ACK":
                    # 异步任务完成后的结果推送由任务系统负责，这里不需要额外发送
                    return None
        else:
            # 没有任务仓储，直接返回空数据
            kline_data = KlineBars(
                symbol=symbol,
                interval=interval,
                bars=[],
                count=0,
                no_data=True,
            )
            result = self._response(
                msg_type="KLINES_DATA",
                request_id=request_id,
                data=kline_data,
            )

        # 第三阶段：发送处理结果
        await self._client_manager.send(client_id, result)
        return None

    async def _handle_get_search_symbols(
        self, data: dict[str, Any], request_id: str | None
    ) -> MessageSuccess:
        """处理 GET_SEARCH_SYMBOLS 请求

        Args:
            data: 请求数据
            request_id: 请求 ID

        Returns:
            搜索结果响应
        """
        if self._exchange_repo is None:
            return self._error_response(
                error_code="EXCHANGE_REPO_NOT_INITIALIZED",
                error_message="Exchange info repository not initialized",
            )

        query = data.get("query", "")
        exchange = data.get("exchange", "BINANCE")
        limit = data.get("limit", 50)
        market_type = data.get("market_type", "ALL")  # 支持 ALL/SPOT/FUTURES

        # 如果查询包含 . 后缀，强制使用 FUTURES 市场类型
        # 因为数据库中期货符号不带 . 后缀，需要单独搜索期货
        if '.' in query:
            market_type = "FUTURES"
            logger.debug(f"[TaskRouter] GET_SEARCH_SYMBOLS: query contains dot suffix, forcing market_type=FUTURES")

        logger.info(f"[TaskRouter] GET_SEARCH_SYMBOLS: query='{query}', exchange='{exchange}', market_type='{market_type}', limit={limit}")

        try:
            # 如果 market_type 为 ALL，同时搜索 SPOT 和 FUTURES
            if market_type == "ALL":
                spot_symbols = await self._exchange_repo.search_symbols(
                    query=query,
                    exchange=exchange,
                    market_type="SPOT",
                    limit=limit,
                )
                futures_symbols = await self._exchange_repo.search_symbols(
                    query=query,
                    exchange=exchange,
                    market_type="FUTURES",
                    limit=limit,
                )
                # 合并结果，现货优先，限制总数不超过 limit
                symbols = (spot_symbols + futures_symbols)[:limit]
                total = len(symbols)
                logger.info(f"[TaskRouter] GET_SEARCH_SYMBOLS: spot={len(spot_symbols)}, futures={len(futures_symbols)}, combined={total}")
            else:
                symbols = await self._exchange_repo.search_symbols(
                    query=query,
                    exchange=exchange,
                    market_type=market_type,
                    limit=limit,
                )
                total = await self._exchange_repo.get_total_count(
                    query=query,
                    exchange=exchange,
                    market_type=market_type,
                )
                logger.info(f"[TaskRouter] GET_SEARCH_SYMBOLS: {market_type} results={len(symbols)}, total={total}")

            # 使用 SearchSymbolsData 模型构建响应
            search_data = SearchSymbolsData(
                symbols=symbols,
                total=total,
                count=len(symbols),
            )
            if symbols:
                symbol_list = [s.ticker for s in symbols[:5]]
                logger.info(f"[TaskRouter] GET_SEARCH_SYMBOLS: returning {len(symbols)} symbols, first 5: {symbol_list}")
            else:
                logger.info(f"[TaskRouter] GET_SEARCH_SYMBOLS: no symbols found for query='{query}'")
            return self._response(
                msg_type="SEARCH_SYMBOLS_DATA",
                request_id=request_id,
                data=search_data,
            )
        except Exception as e:
            logger.error(f"搜索交易对失败: {e}")
            return self._error_response(
                error_code="SEARCH_SYMBOLS_FAILED",
                error_message=f"搜索失败: {str(e)}",
            )

    async def _handle_get_resolve_symbol(
        self, data: dict[str, Any], request_id: str | None
    ) -> MessageSuccess:
        """处理 GET_RESOLVE_SYMBOL 请求

        Args:
            data: 请求数据
            request_id: 请求 ID

        Returns:
            交易对详情响应
        """
        if self._exchange_repo is None:
            return self._error_response(
                error_code="EXCHANGE_REPO_NOT_INITIALIZED",
                error_message="Exchange info repository not initialized",
            )

        symbol = data.get("symbol")
        if not symbol:
            return self._error_response(
                error_code="INVALID_PARAMETERS",
                error_message="Missing symbol parameter",
            )

        # 记录解析品种请求的详细信息（DEBUG级别）
        logger.info(f"[RESOLVE_SYMBOL] 收到解析品种请求: symbol={symbol}")

        try:
            # 使用 SemanticSymbol 解析 symbol，自动判断市场类型
            parsed = parse_semantic_symbol(symbol)
            # 根据是否有合约类型判断市场类型
            market_type = "FUTURES" if parsed.is_futures else "SPOT"

            logger.debug(
                f"[RESOLVE_SYMBOL] 解析后: exchange={parsed.exchange}, "
                f"is_futures={parsed.is_futures}, market_type={market_type}"
            )

            symbol_info = await self._exchange_repo.resolve_symbol(
                symbol=symbol,
                exchange=parsed.exchange,
                market_type=market_type,
            )

            # 如果在指定市场找不到，尝试在另一个市场查找
            if symbol_info is None:
                fallback_market = "SPOT" if market_type == "FUTURES" else "FUTURES"
                symbol_info = await self._exchange_repo.resolve_symbol(
                    symbol=symbol,
                    exchange=parsed.exchange,
                    market_type=fallback_market,
                )

            if symbol_info is None:
                return self._error_response(
                    error_code="SYMBOL_NOT_FOUND",
                    error_message=f"Symbol not found: {symbol}",
                )

            # 直接返回 SymbolInfo 模型，无需包装
            # SymbolInfo 继承自 CamelCaseModel，序列化时自动转换为 camelCase
            logger.info(
                f"[RESOLVE_SYMBOL] 解析成功: symbol={symbol} -> "
                f"name={symbol_info.name}, ticker={symbol_info.ticker}, "
                f"pricescale={symbol_info.pricescale}"
            )
            return self._response(
                msg_type="SYMBOL_DATA",
                request_id=request_id,
                data=symbol_info,
            )
        except ValueError as e:
            # 处理无效 symbol 格式
            logger.error(f"Symbol 格式错误: {e}")
            return self._error_response(
                error_code="INVALID_SYMBOL_FORMAT",
                error_message=f"无效的 symbol 格式: {str(e)}",
            )
        except Exception as e:
            logger.error(f"解析交易对失败: {e}")
            return self._error_response(
                error_code="RESOLVE_SYMBOL_FAILED",
                error_message=f"解析失败: {str(e)}",
            )

    async def _handle_alert_request(
        self, action: str, data: dict[str, Any], request_id: str | None
    ) -> MessageSuccess:
        """处理告警配置请求

        Args:
            action: 操作类型 (create, list, update, delete, enable, disable, list_signals)
            data: 请求数据
            request_id: 请求 ID

        Returns:
            告警操作响应
        """
        if self._alert_handler is None:
            return self._error_response(
                error_code="HANDLER_NOT_INITIALIZED",
                error_message="Alert handler not initialized",
            )

        handlers = {
            "create": self._alert_handler.handle_create_alert_config,
            "list": self._alert_handler.handle_list_alert_configs,
            "update": self._alert_handler.handle_update_alert_config,
            "delete": self._alert_handler.handle_delete_alert_config,
            # 注意：启用/禁用已合并到 UPDATE 操作中，通过 isEnabled 字段控制
            "list_signals": self._alert_handler.handle_list_signals,
        }

        handler = handlers.get(action)
        if handler:
            return await handler(data, request_id)

        return self._error_response(
            error_code="UNKNOWN_ACTION",
            error_message=f"Unknown alert action: {action}",
        )

    async def _handle_subscribe(
        self, client_id: str, data: dict[str, Any], request_id: str | None = None
    ) -> MessageSuccess:
        """处理订阅请求

        Args:
            client_id: 客户端 ID
            data: 请求数据
            request_id: 请求 ID（用于三阶段模式关联）

        Returns:
            响应消息
        """
        subscriptions = data.get("subscriptions", [])

        if not subscriptions:
            return self._error_response(
                error_code="INVALID_PARAMETERS",
                error_message="No subscriptions provided",
            )

        # 使用订阅管理器处理订阅
        inserted_count = await self._subscription_manager.subscribe_batch(
            client_id, subscriptions
        )

        logger.debug(
            f"客户端 {client_id} 订阅 {len(subscriptions)} 个键，"
            f"新增数据库记录 {inserted_count} 个"
        )

        # 专门监控账户信息订阅（BINANCE:SPOT@USERDATA 或 BINANCE:FUTURES@USERDATA）
        account_subs = [s for s in subscriptions if "@USERDATA" in s]
        if account_subs:
            logger.info(
                f"[账户订阅监控] 客户端 {client_id} 订阅账户信息: {account_subs}"
            )

        return self._response(
            msg_type="SUBSCRIPTION_DATA",  # 遵循07-websocket-protocol.md规范
            request_id=request_id,
            data=SubscribeData(
                subscriptions=subscriptions,
            ),
        )

    async def _handle_unsubscribe(
        self, client_id: str, data: dict[str, Any], request_id: str | None = None
    ) -> MessageSuccess:
        """处理取消订阅请求

        Args:
            client_id: 客户端 ID
            data: 请求数据
            request_id: 请求 ID（用于三阶段模式关联）

        Returns:
            响应消息
        """
        all_subs = data.get("all", False)
        subscriptions = data.get("subscriptions", [])

        if all_subs:
            # 取消所有订阅
            deleted_keys = await self._subscription_manager.unsubscribe_all(client_id)
            logger.debug(f"客户端 {client_id} 取消全部 {len(deleted_keys)} 个订阅")

            # 专门监控账户信息取消订阅
            account_unsubs = [k for k in deleted_keys if "@USERDATA" in k]
            if account_unsubs:
                logger.info(
                    f"[账户订阅监控] 客户端 {client_id} 取消全部账户信息订阅: {account_unsubs}"
                )

            return self._response(
                msg_type="SUBSCRIPTION_DATA",  # 遵循07-websocket-protocol.md规范
                request_id=request_id,
                data=UnsubscribeData(
                    status="success",
                ),
            )

        if not subscriptions:
            return self._error_response(
                error_code="INVALID_PARAMETERS",
                error_message="No subscriptions provided",
            )

        # 批量取消订阅
        deleted_count = await self._subscription_manager.unsubscribe_batch(
            client_id, subscriptions
        )

        logger.debug(
            f"客户端 {client_id} 取消 {len(subscriptions)} 个订阅，"
            f"删除数据库记录 {deleted_count} 个"
        )

        # 专门监控账户信息取消订阅（BINANCE:SPOT@USERDATA 或 BINANCE:FUTURES@USERDATA）
        account_unsubs = [s for s in subscriptions if "@USERDATA" in s]
        if account_unsubs:
            logger.info(
                f"[账户订阅监控] 客户端 {client_id} 取消账户信息订阅: {account_unsubs}"
            )

        return self._response(
            msg_type="UNSUBSCRIBE_DATA",  # 遵循07-websocket-protocol.md规范
            request_id=request_id,
            data=UnsubscribeData(
                status="success",
            ),
        )

    # ========== 订单交易处理方法 ==========

    async def _handle_create_order(
        self, client_id: str, data: dict[str, Any], request_id: str | None
    ) -> None:
        """处理创建订单请求

        使用 Pydantic 模型验证订单数据，确保符合协议规范。
        将订单请求写入 order_tasks 表，触发 binance-service 执行。

        注意：创建任务后不立即发送响应，而是由 _on_order_task_notification
        通知处理后发送最终响应。

        Args:
            client_id: 客户端 ID
            data: 请求数据
            request_id: 请求 ID（必须存在于顶层字段）

        Returns:
            None（响应由通知处理发送）
        """
        # 验证 requestId 必须存在（设计要求：requestId 必须在顶层）
        if not request_id:
            error_resp = self._error_response(
                error_code="MISSING_REQUEST_ID",
                error_message="requestId is required in top-level field",
                request_id=None,
            )
            await self._client_manager.send(client_id, error_resp)
            return

        if self._order_tasks_repo is None:
            error_resp = self._error_response(
                error_code="ORDER_REPO_NOT_INITIALIZED",
                error_message="Order tasks repository not initialized",
                request_id=request_id,
            )
            await self._client_manager.send(client_id, error_resp)
            return

        # 根据市场类型选择正确的模型验证订单数据
        try:
            symbol = data.get("symbol", "")
            # 期货: symbol 包含 .PERP 后缀
            if ".PERP" in symbol.upper():
                validated_order = FuturesCreateOrderRequest.model_validate(data)
            else:
                validated_order = SpotCreateOrderRequest.model_validate(data)
        except Exception as e:
            error_resp = self._error_response(
                error_code="INVALID_PARAMETERS",
                error_message=f"Invalid order data: {str(e)}",
                request_id=request_id,
            )
            await self._client_manager.send(client_id, error_resp)
            return

        try:
            # 创建订单任务（requestId 存为顶层字段，不是 payload）
            task_id = await self._order_tasks_repo.create_order_task(
                task_type="order.create",
                request_id=request_id,  # 顶层字段
                payload=validated_order.model_dump(),  # payload 使用蛇形命名
            )

            logger.info(
                f"Created order task: id={task_id}, symbol={validated_order.symbol}, "
                f"side={validated_order.side}, type={validated_order.type}"
            )

            # 注册任务与客户端的映射（用于订单完成后推送结果）
            self._client_manager.register_task(task_id, client_id)

            # 不发送响应，等待币安服务处理完成后的通知
            # 最终响应由 _on_order_task_notification 发送
        except Exception as e:
            logger.error(f"创建订单任务失败: {e}")
            error_resp = self._error_response(
                error_code="ORDER_CREATE_FAILED",
                error_message=f"Failed to create order: {str(e)}",
                request_id=request_id,
            )
            await self._client_manager.send(client_id, error_resp)

    async def _handle_get_order(
        self, client_id: str, data: dict[str, Any], request_id: str | None
    ) -> None:
        """处理查询单个订单请求

        使用 Pydantic 模型验证查询参数。
        创建任务后不立即发送响应，而是由 _on_order_task_notification
        通知处理后发送最终响应。

        Args:
            client_id: 客户端 ID
            data: 请求数据
            request_id: 请求 ID

        Returns:
            None（响应由通知处理发送）
        """
        if self._order_tasks_repo is None:
            error_resp = self._error_response(
                error_code="ORDER_REPO_NOT_INITIALIZED",
                error_message="Order tasks repository not initialized",
                request_id=request_id,
            )
            await self._client_manager.send(client_id, error_resp)
            return

        # 使用 Pydantic 模型验证查询参数
        try:
            validated_query = GetOrderRequest.model_validate(data)
        except Exception as e:
            error_resp = self._error_response(
                error_code="INVALID_PARAMETERS",
                error_message=f"Invalid query parameters: {str(e)}",
                request_id=request_id,
            )
            await self._client_manager.send(client_id, error_resp)
            return

        # 获取 origClientOrderId（可以是 None，但验证器会确保至少有一个）
        # 用于查询对应的订单任务
        orig_client_order_id = validated_query.orig_client_order_id
        order_id = validated_query.order_id

        # 验证：至少提供一个查询条件（orderId 或 origClientOrderId）
        # 所有订单查询都通过币安 API，不查本地缓存（保持订单状态统一）
        if not orig_client_order_id and not order_id:
            error_resp = self._error_response(
                error_code="MISSING_QUERY_PARAMETERS",
                error_message="Either orderId or origClientOrderId is required for order query",
                request_id=request_id,
            )
            await self._client_manager.send(client_id, error_resp)
            return

        symbol = validated_query.symbol

        try:
            # 构建查询参数，统一通过 order.query 任务让 binance-service 调用币安 API
            query_request_id = request_id or (
                f"query_{orig_client_order_id}"
                if orig_client_order_id
                else f"query_{order_id}"
            )
            query_payload: dict[str, Any] = {"symbol": symbol}

            # order_id 和 orig_client_order_id 都传给币安 API（API 会自动识别）
            if order_id:
                query_payload["order_id"] = order_id
            if orig_client_order_id:
                query_payload["orig_client_order_id"] = orig_client_order_id

            task_id = await self._order_tasks_repo.create_order_task(
                task_type="order.query",
                request_id=query_request_id,
                payload=query_payload,
            )

            logger.info(
                f"Created order query task: id={task_id}, symbol={symbol}, orderId={order_id}, origClientOrderId={orig_client_order_id}"
            )

            # 注册任务与客户端的映射（用于订单完成后推送结果）
            self._client_manager.register_task(task_id, client_id)

            # 不发送响应，等待币安服务处理完成后的通知
            # 最终响应由 _on_order_task_notification 发送

        except Exception as e:
            logger.error(f"查询订单失败: {e}")
            error_resp = self._error_response(
                error_code="ORDER_QUERY_FAILED",
                error_message=f"Failed to query order: {str(e)}",
                request_id=request_id,
            )
            await self._client_manager.send(client_id, error_resp)

    async def _handle_list_orders(
        self, client_id: str, data: dict[str, Any], request_id: str | None
    ) -> MessageSuccess:
        """处理查询订单列表请求

        Args:
            client_id: 客户端 ID
            data: 请求数据
            request_id: 请求 ID

        Returns:
            订单列表响应
        """
        if self._order_tasks_repo is None:
            return self._error_response(
                error_code="ORDER_REPO_NOT_INITIALIZED",
                error_message="Order tasks repository not initialized",
            )

        try:
            # 解析过滤参数
            task_type = data.get("taskType")  # order.create, order.cancel, order.query
            status = data.get("status")
            symbol = data.get("symbol")
            limit = data.get("limit", 100)
            offset = data.get("offset", 0)

            # 查询订单任务列表
            tasks = await self._order_tasks_repo.list_order_tasks(
                task_type=task_type,
                status=status,
                symbol=symbol,
                limit=limit,
                offset=offset,
            )

            # 使用 OrderListResponseData 模型构建响应
            order_list = []
            for task in tasks:
                payload = task.get("payload", {})
                order_data = OrderData(
                    client_order_id=payload.get("new_client_order_id"),
                    binance_order_id=task.get("result", {}).get("order_id"),
                    market_type=payload.get("market_type", "FUTURES"),
                    symbol=payload.get("symbol", ""),
                    status=task.get("status"),
                    data=task.get("result", {}),
                    created_at=task.get("created_at"),
                    updated_at=task.get("updated_at"),
                )
                order_list.append(order_data)

            response_data = OrderListResponseData(
                orders=order_list,
                count=len(order_list),
            )

            return self._response(
                msg_type="ORDER_LIST_DATA",
                request_id=request_id,
                data=response_data,
            )
        except Exception as e:
            logger.error(f"查询订单列表失败: {e}")
            return self._error_response(
                error_code="ORDER_LIST_FAILED",
                error_message=f"Failed to list orders: {str(e)}",
            )

    async def _handle_cancel_order(
        self, client_id: str, data: dict[str, Any], request_id: str | None
    ) -> MessageSuccess:
        """处理取消订单请求

        使用 Pydantic 模型验证取消订单参数。

        Args:
            client_id: 客户端 ID
            data: 请求数据
            request_id: 请求 ID（必须存在于顶层字段）

        Returns:
            订单数据响应
        """
        # 验证 requestId 必须存在（设计要求：requestId 必须在顶层）
        if not request_id:
            return self._error_response(
                error_code="MISSING_REQUEST_ID",
                error_message="requestId is required in top-level field",
                request_id=None,
            )

        if self._order_tasks_repo is None:
            return self._error_response(
                error_code="ORDER_REPO_NOT_INITIALIZED",
                error_message="Order tasks repository not initialized",
                request_id=request_id,
            )

        # 使用 Pydantic 模型验证取消订单参数
        try:
            validated_cancel = CancelOrderRequest.model_validate(data)
        except Exception as e:
            return self._error_response(
                error_code="INVALID_PARAMETERS",
                error_message=f"Invalid cancel parameters: {str(e)}",
                request_id=request_id,
            )

        # 使用 order_id 或 orig_client_order_id 作为取消依据（两者是 OR 关系）
        order_id = validated_cancel.order_id
        orig_client_order_id = validated_cancel.orig_client_order_id

        try:
            # 创建取消订单任务（requestId 存为顶层字段，不是 payload）
            task_id = await self._order_tasks_repo.create_order_task(
                task_type="order.cancel",
                request_id=request_id,  # 顶层字段
                payload=validated_cancel.model_dump(),  # payload 不含 requestId
            )

            logger.info(
                f"Created cancel order task: id={task_id}, orderId={order_id}, origClientOrderId={orig_client_order_id}"
            )

            # 使用 OrderCancelResponseData 模型构建响应
            response_data = OrderCancelResponseData(
                task_id=task_id,
                status="PENDING",
                order_id=str(order_id) if order_id else None,
                orig_client_order_id=orig_client_order_id,
            )

            return self._response(
                msg_type="ORDER_DATA",
                request_id=request_id,
                data=response_data,
            )
        except Exception as e:
            logger.error(f"创建取消订单任务失败: {e}")
            return self._error_response(
                error_code="ORDER_CANCEL_FAILED",
                error_message=f"Failed to cancel order: {str(e)}",
                request_id=request_id,
            )

    async def _handle_modify_order(
        self, client_id: str, data: dict[str, Any], request_id: str | None
    ) -> None:
        """处理修改订单请求

        Args:
            client_id: 客户端 ID
            data: 请求数据
            request_id: 请求 ID
        """
        if self._order_tasks_repo is None:
            await self._client_manager.send(
                client_id,
                self._error_response(
                    error_code="ORDER_REPO_NOT_INITIALIZED",
                    error_message="Order tasks repository not initialized",
                    request_id=request_id,
                ),
            )
            return

        # 解析 symbol 判断市场类型
        raw_symbol = data.get("symbol", "")
        if raw_symbol.upper().startswith("BINANCE:"):
            clean_symbol = raw_symbol[len("BINANCE:") :]
            if clean_symbol.upper().endswith(".PERP"):
                market_type = "FUTURES"
                symbol = clean_symbol[:-5]
            else:
                market_type = "SPOT"
                symbol = clean_symbol
        else:
            # 无前缀，默认当作期货处理（向后兼容）
            market_type = "FUTURES"
            symbol = raw_symbol

        # 根据市场类型选择验证模型
        # 注意：期货和现货使用不同的 API
        # - 期货: order.modify - 可修改价格和数量
        # - 现货: order.amend.keepPriority - 只能减少数量
        try:
            if market_type == "FUTURES":
                # 验证期货修改订单请求
                validated_modify = FuturesModifyOrderRequest.model_validate(data)
                # 添加 market_type 到 payload（用于后续路由）
                payload = validated_modify.model_dump()
                payload["market_type"] = market_type

            else:
                # 验证现货修改订单请求
                validated_modify = SpotAmendOrderRequest.model_validate(data)
                # 添加 market_type 到 payload（用于后续路由）
                payload = validated_modify.model_dump()
                payload["market_type"] = market_type

        except Exception as e:
            logger.error(f"验证修改订单请求失败: {e}")
            await self._client_manager.send(
                client_id,
                self._error_response(
                    error_code="ORDER_MODIFY_VALIDATION_FAILED",
                    error_message=f"Invalid modify order request: {str(e)}",
                    request_id=request_id,
                ),
            )
            return

        try:
            # 创建修改订单任务（requestId 存为顶层字段，不是 payload）
            task_id = await self._order_tasks_repo.create_order_task(
                task_type="order.modify",
                request_id=request_id,  # 顶层字段
                payload=payload,  # payload 不含 requestId
            )

            logger.info(f"Created modify order task: id={task_id}, symbol={symbol}, market={market_type}")

            # 注册任务与客户端的映射（用于订单完成后推送结果）
            self._client_manager.register_task(task_id, client_id)

            # 不发送响应，等待币安服务处理完成后的通知
            # 最终响应由 _on_order_task_notification 发送
        except Exception as e:
            logger.error(f"创建修改订单任务失败: {e}")
            await self._client_manager.send(
                client_id,
                self._error_response(
                    error_code="ORDER_MODIFY_FAILED",
                    error_message=f"Failed to modify order: {str(e)}",
                    request_id=request_id,
                ),
            )

    async def _handle_get_open_orders(
        self, client_id: str, data: dict[str, Any], request_id: str | None
    ) -> MessageSuccess:
        """处理查询当前挂单请求

        Args:
            client_id: 客户端 ID
            data: 请求数据
            request_id: 请求 ID

        Returns:
            订单列表响应
        """
        if self._order_tasks_repo is None:
            return self._error_response(
                error_code="ORDER_REPO_NOT_INITIALIZED",
                error_message="Order tasks repository not initialized",
            )

        try:
            # 查询 pending 或 processing 状态的订单
            tasks = await self._order_tasks_repo.list_order_tasks(
                task_type="order.create",
                status="pending",
                limit=100,
                offset=0,
            )

            # 使用 OpenOrdersResponseData 模型构建响应
            order_list = []
            for task in tasks:
                payload = task.get("payload", {})
                order_data = OrderData(
                    client_order_id=payload.get("new_client_order_id"),
                    binance_order_id=task.get("result", {}).get("order_id"),
                    market_type=payload.get("market_type", "FUTURES"),
                    symbol=payload.get("symbol", ""),
                    status=task.get("status"),
                    data=task.get("result", {}),
                    created_at=task.get("created_at"),
                    updated_at=task.get("updated_at"),
                )
                order_list.append(order_data)

            response_data = OpenOrdersResponseData(
                orders=order_list,
                count=len(order_list),
            )

            return self._response(
                msg_type="ORDER_LIST_DATA",
                request_id=request_id,
                data=response_data,
            )
        except Exception as e:
            logger.error(f"查询挂单失败: {e}")
            return self._error_response(
                error_code="ORDER_OPEN_LIST_FAILED",
                error_message=f"Failed to get open orders: {str(e)}",
            )

    def _response(
        self,
        msg_type: str,
        request_id: str | None,
        data: CamelCaseModel,
    ) -> MessageSuccess:
        """构建成功响应

        使用 Pydantic 模型确保响应符合协议规范。

        严格遵循07-websocket-protocol.md规范：
        - 使用 type 字段表示数据类型（如 KLINES_DATA, CONFIG_DATA 等）
        - data 必须是 Pydantic CamelCaseModel 实例

        Args:
            msg_type: 消息类型（如 KLINES_DATA, CONFIG_DATA, SUBSCRIPTION_DATA 等）
            request_id: 请求 ID
            data: 响应数据（Pydantic CamelCaseModel 模型）

        Returns:
            MessageSuccess 模型实例
        """
        response = MessageSuccess(
            type=msg_type,
            request_id=request_id or "",
            protocol_version=PROTOCOL_VERSION,
            timestamp=self._timestamp_ms(),
            data=data,  # 直接传入模型实例，让 model_serializer 自动序列化
        )
        return response

    def _error_response(
        self,
        error_code: str,
        error_message: str,
        request_id: str | None = None,
    ) -> MessageError:
        """构建错误响应

        使用 Pydantic 模型确保响应符合协议规范。

        严格遵循07-websocket-protocol.md规范：
        - type 字段值为 "ERROR"（在顶层）
        - 错误详情放在 data 内部（使用 ErrorData 模型）

        Args:
            error_code: 错误代码
            error_message: 错误信息
            request_id: 请求 ID

        Returns:
            MessageError 模型实例
        """
        error_data = ErrorData(
            error_code=error_code,
            error_message=error_message,
        )
        return MessageError(
            request_id=request_id or "",
            timestamp=self._timestamp_ms(),
            data=error_data,
        )

    async def _create_async_task(
        self,
        client_id: str,
        task_type: str,
        payload: dict[str, Any],
        store_result: bool = True,
        request_id: str | None = None,
    ) -> MessageSuccess | MessageError:
        """创建异步任务（异步任务三阶段模式第一阶段）

        Args:
            client_id: 客户端 ID
            task_type: 任务类型
            payload: 任务参数
            store_result: 是否存储结果到 tasks.result 字段（get_klines 设为 False）
            request_id: 请求 ID（用于关联 ack 确认和最终响应）

        Returns:
            ack 确认消息
        """
        if self._tasks_repo is None:
            return self._error_response(
                error_code="TASKS_REPOSITORY_NOT_SET",
                error_message="Tasks repository not initialized",
            )

        try:
            # 将 requestId 添加到 payload 中（用于三阶段模式关联）
            # 创建任务（request_id 已提升到 tasks 表顶层字段）
            task_id = await self._tasks_repo.create_task(
                task_type=task_type,
                payload=payload,
                request_id=request_id,
            )

            # 注册任务与客户端的映射（用于推送结果）
            self._client_manager.register_task(task_id, client_id)

            logger.debug(
                f"创建异步任务: client_id={client_id}, "
                f"task_type={task_type}, task_id={task_id}, request_id={request_id}, store_result={store_result}"
            )

            # 返回 ack 确认消息（三阶段模式第一阶段）
            # 严格遵循07-websocket-protocol.md规范：type 值为 "ACK"
            # 注意：taskId 不返回给客户端，仅在服务端内部使用
            # data 使用 AckData 模型（必须传 BaseModel 实例，禁止传字典）
            ack = MessageSuccess(
                type="ACK",
                request_id=request_id or "",
                protocol_version=PROTOCOL_VERSION,
                timestamp=self._timestamp_ms(),
                data=AckData(),
            )
            # 返回 MessageSuccess 实例，禁止返回字典（确保类型安全）
            return ack

        except Exception as e:
            logger.error(f"创建任务失败: {task_type}, {e}")
            return self._error_response(
                error_code="TASK_CREATION_FAILED",
                error_message=f"Failed to create task: {str(e)}",
            )

    def _timestamp_ms(self) -> int:
        """获取当前时间戳（毫秒）"""
        import time

        return int(time.time() * 1000)

    def _align_to_kline_open_time(self, timestamp_ms: int, interval: str) -> int:
        """将时间戳对齐到 K 线开盘时间

        TradingView API 要求 from_time 和 to_time 必须对齐到 K 线开盘时间。
        支持多种 interval 格式：
        - 数字格式（分钟）："1", "5", "15", "60", "1440"
        - TradingView 格式："1D", "D", "W", "M"

        Args:
            timestamp_ms: 时间戳（毫秒）
            interval: K线周期

        Returns:
            对齐后的时间戳（毫秒）
        """
        # 处理 TradingView 格式
        if interval == "D" or interval == "1D":
            interval_sec = 24 * 60 * 60  # 1天 = 86400秒
        elif interval == "W" or interval == "1W":
            interval_sec = 7 * 24 * 60 * 60  # 1周 = 604800秒
        elif interval == "M" or interval == "1M":
            interval_sec = 30 * 24 * 60 * 60  # 1月 ≈ 2592000秒（月线按30天近似）
        else:
            # 数字格式（分钟）
            try:
                interval_value = int(interval)
                interval_sec = interval_value * 60
            except (ValueError, TypeError):
                interval_sec = 60  # 默认1分钟

        # 将毫秒转换为秒并对齐
        timestamp_sec = timestamp_ms // 1000
        aligned_sec = (timestamp_sec // interval_sec) * interval_sec

        return aligned_sec * 1000  # 转回毫秒

    # ========== 策略元数据处理方法 ==========

    async def _handle_get_strategy_metadata(
        self, data: dict[str, Any], request_id: str | None
    ) -> MessageSuccess:
        """处理获取所有策略元数据请求

        严格遵循 07-websocket-protocol.md 设计：
        - 响应类型: STRATEGY_METADATA_DATA
        - 返回 strategies 数组

        Args:
            data: 请求数据
            request_id: 请求 ID

        Returns:
            策略元数据响应
        """
        if self._strategy_metadata_repo is None:
            return self._error_response(
                error_code="STRATEGY_REPO_NOT_INITIALIZED",
                error_message="Strategy metadata repository not initialized",
                request_id=request_id,
            )

        try:
            strategies_raw = await self._strategy_metadata_repo.find_all()

            # 转换数据库记录为响应模型（自动转为 camelCase）
            strategies = []
            for strategy in strategies_raw:
                # 解析 params 字段（JSON 字符串 -> 对象数组）
                params_str = strategy.get("params", "[]")
                if isinstance(params_str, str):
                    try:
                        params_list = json.loads(params_str)
                    except (json.JSONDecodeError, TypeError):
                        params_list = []
                else:
                    params_list = params_str or []

                # 构建响应模型（使用 CamelCaseModel 自动转换字段名）
                strategy_resp = StrategyMetadataResponse(
                    type=strategy.get("type", ""),
                    name=strategy.get("name", ""),
                    description=strategy.get("description", ""),
                    params=params_list,
                    created_at=strategy.get("created_at"),
                    updated_at=strategy.get("updated_at"),
                )
                strategies.append(strategy_resp.model_dump())

            # 构建响应
            response = StrategyMetadataListResponse(strategies=strategies)

            return self._response(
                msg_type="STRATEGY_METADATA_DATA",
                request_id=request_id,
                data=response,
            )
        except Exception as e:
            logger.exception("Failed to get strategy metadata: %s", e)
            return self._error_response(
                error_code="GET_STRATEGY_METADATA_FAILED",
                error_message=f"Failed to get strategy metadata: {str(e)}",
                request_id=request_id,
            )

    async def _handle_get_strategy_metadata_by_type(
        self, data: dict[str, Any], request_id: str | None
    ) -> MessageSuccess:
        """处理获取指定策略元数据请求

        严格遵循 07-websocket-protocol.md 设计：
        - 响应类型: STRATEGY_METADATA_DATA
        - 返回 strategy 对象

        Args:
            data: 请求数据（包含 strategy_type）
            request_id: 请求 ID

        Returns:
            策略元数据响应
        """
        if self._strategy_metadata_repo is None:
            return self._error_response(
                error_code="STRATEGY_REPO_NOT_INITIALIZED",
                error_message="Strategy metadata repository not initialized",
                request_id=request_id,
            )

        strategy_type = data.get("strategy_type") or data.get("strategyType")
        if not strategy_type:
            return self._error_response(
                error_code="INVALID_PARAMETERS",
                error_message="Missing strategy_type parameter",
                request_id=request_id,
            )

        try:
            strategy = await self._strategy_metadata_repo.find_by_type(strategy_type)

            if strategy is None:
                return self._error_response(
                    error_code="STRATEGY_NOT_FOUND",
                    error_message=f"Strategy not found: {strategy_type}",
                    request_id=request_id,
                )

            # 转换数据库字典为 StrategyMetadataResponse 模型
            strategy_resp = StrategyMetadataResponse(
                type=strategy.get("type", ""),
                name=strategy.get("name", ""),
                description=strategy.get("description", ""),
                params=strategy.get("params", []),
                created_at=strategy.get("created_at"),
                updated_at=strategy.get("updated_at"),
            )

            # 包装为设计文档规定的格式: data.strategy
            strategy_data = StrategyMetadataByTypeData(strategy=strategy_resp)

            return self._response(
                msg_type="STRATEGY_METADATA_DATA",
                request_id=request_id,
                data=strategy_data,
            )
        except Exception as e:
            logger.exception("Failed to get strategy metadata by type: %s", e)
            return self._error_response(
                error_code="GET_STRATEGY_METADATA_BY_TYPE_FAILED",
                error_message=f"Failed to get strategy metadata: {str(e)}",
                request_id=request_id,
            )
