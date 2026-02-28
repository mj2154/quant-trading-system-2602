"""
任务路由器 - 支持新任务表机制

将客户端请求路由到相应的处理函数：
- 直接查询类型：config, search_symbols, resolve_symbol（API网关直接处理）
- 异步任务类型：get_klines, get_server_time, get_quotes（INSERT tasks表）
- 告警类型：create_alert_config, list_alert_configs, update_alert_config, delete_alert_config, enable_alert_config, disable_alert_config, list_signals

遵循 SUBSCRIPTION_AND_REALTIME_DATA.md 设计：
- 异步任务通过 tasks 表触发通知
- 任务完成后通过 task.completed 通知返回结果

K线历史数据查询策略（重要）：
1. 先根据周期对齐时间（from_time, to_time）
2. 查询 klines_history 表，验证起始和结束两个时间点的数据
3. 如果任意一个不存在，创建异步任务去币安API获取
4. 如果两个都存在，直接从数据库返回数据（不走异步任务）
5. **只验证端点，不验证中间数据**（中间数据缺失不影响返回）
"""

import logging
from typing import Any

from ..db.tasks_repository import TasksRepository
from ..db.exchange_info_repository import ExchangeInfoRepository
from ..db.alert_signal_repository import AlertSignalRepository
from ..db.strategy_signals_repository import StrategySignalsRepository
from ..models.trading.kline_models import KlineBars, KlineBar
from ..protocol.messages import MessageAck
from .subscription_manager import SubscriptionManager
from .client_manager import ClientManager
from .alert_handler import AlertHandler

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

        # 交易所信息仓储
        self._exchange_repo: ExchangeInfoRepository | None = None

        # 告警处理器
        self._alert_handler: AlertHandler | None = None

    def set_tasks_repository(self, tasks_repo: TasksRepository) -> None:
        """设置新任务仓储实例

        Args:
            tasks_repo: 新任务仓储实例（基于 tasks 表）
        """
        self._tasks_repo = tasks_repo

    def set_exchange_info_repository(self, exchange_repo: ExchangeInfoRepository) -> None:
        """设置交易所信息仓储实例

        Args:
            exchange_repo: 交易所信息仓储实例
        """
        self._exchange_repo = exchange_repo

    def set_alert_repository(
        self,
        alert_repo: AlertSignalRepository,
        signals_repo: StrategySignalsRepository | None = None,
    ) -> None:
        """设置告警仓储实例

        Args:
            alert_repo: 告警信号仓储实例
            signals_repo: 可选，策略信号仓储实例
        """
        self._alert_handler = AlertHandler(alert_repo, signals_repo)
        logger.info("AlertHandler initialized")

    @property
    def subscription_manager(self) -> SubscriptionManager:
        """获取订阅管理器实例"""
        return self._subscription_manager

    def _create_ack(self, request_id: str | None) -> dict[str, Any]:
        """创建 ACK 确认响应（三阶段模式第一阶段）

        严格遵循 07-websocket-protocol.md 规范：
        - type 字段值为 "ACK"
        - data 为空对象 {}
        - 返回 requestId 用于关联

        Args:
            request_id: 请求 ID（用于关联 ack 确认和最终响应）

        Returns:
            ACK 确认消息字典
        """
        ack = MessageAck(request_id=request_id)
        return ack.model_dump(by_alias=True)

    async def _send_ack_and_process(
        self, client_id: str, request_id: str | None, process_fn
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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
        msg_type = request.get("type", "GET")
        data = request.get("data", {})
        request_id = request.get("requestId")

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
            symbols = data.get("symbols", [])
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

        elif msg_type == "ENABLE_ALERT_CONFIG":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_alert_request("enable", data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        elif msg_type == "DISABLE_ALERT_CONFIG":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_alert_request("disable", data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        elif msg_type == "LIST_SIGNALS":
            # 第一阶段：发送 ACK
            await self._client_manager.send(client_id, self._create_ack(request_id))
            # 第二阶段：处理请求
            result = await self._handle_alert_request("list_signals", data, request_id)
            # 第三阶段：发送结果
            await self._client_manager.send(client_id, result)
            return None

        # ========== 未知类型 ==========
        else:
            return {
                "protocolVersion": "2.0",
                "type": "ERROR",
                "requestId": request_id,
                "timestamp": self._timestamp(),
                "data": {
                    "errorCode": "UNKNOWN_TYPE",
                    "errorMessage": f"Unknown type: {msg_type}",
                },
            }

    # ========== 直接查询处理方法（遵循07-websocket-protocol.md：顶层type是具体操作）==========

    def _handle_get_config(self, request_id: str | None) -> dict[str, Any]:
        """处理 GET_CONFIG 请求

        Args:
            request_id: 请求 ID

        Returns:
            配置数据响应
        """
        return self._response(
            msg_type="CONFIG_DATA",
            request_id=request_id,
            data={
                "type": "config",
                "supports_search": True,
                "supports_group_request": False,
                "supports_marks": False,
                "supports_timescale_marks": False,
                "supports_time": True,
                "exchanges": [
                    {
                        "name": "BINANCE",
                        "has_intraday": True,
                        "has_daily": True,
                        "has_weekly_and_monthly": True,
                        "has_empty_bars": True,
                        "shown_symbols": ["BINANCE:*"],
                        "ticker": "BINANCE:*",
                    }
                ],
                "symbols_types": [
                    {"name": "Index", "value": "index"},
                    {"name": "Stock", "value": "stock"},
                    {"name": "Forex", "value": "forex"},
                    {"name": "Futures", "value": "futures"},
                    {"name": "Crypto", "value": "crypto"},
                    {"name": "CFD", "value": "cfd"},
                ],
                "currency_codes": ["USDT", "BTC", "ETH", "BNB", "BUSD"],
                "supported_resolutions": [
                    "1", "5", "15", "60", "240", "1D", "1W", "1M"
                ],
                "intraday_multipliers": ["1", "5", "15", "60", "240"],
            },
        )

    def _handle_get_metrics(self, request_id: str | None) -> dict[str, Any]:
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

        return self._response(
            msg_type="METRICS_DATA",
            request_id=request_id,
            data={
                "type": "metrics",
                "pendingTasks": pending_count,
                "connectedClients": 0,
            },
        )

    async def _handle_get_klines(
        self, client_id: str, data: dict[str, Any], request_id: str | None
    ) -> dict[str, Any]:
        """处理 GET_KLINES 请求（严格遵循07-websocket-protocol.md：三阶段模式）

        协议要求：无论缓存是否命中，都必须先返回 ACK 确认。

        Args:
            client_id: 客户端 ID
            data: 请求数据
            request_id: 请求 ID

        Returns:
            None（响应已由内部发送）
        """
        symbol = data.get("symbol")
        interval = data.get("interval")
        from_time = data.get("from_time")
        to_time = data.get("to_time")

        if not all([symbol, interval, from_time, to_time]):
            # 参数错误，也需要先发送 ACK 再发送错误
            await self._client_manager.send(client_id, self._create_ack(request_id))
            error_resp = self._error_response(
                error_code="INVALID_PARAMETERS",
                error_message="Missing required parameters",
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
                logger.info(
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
                    data={
                        "type": "klines",
                        **kline_data.model_dump(),
                    },
                )
            else:
                missing = []
                if not endpoints["from_exists"]:
                    missing.append("from_time")
                if not endpoints["to_exists"]:
                    missing.append("to_time")
                logger.info(
                    f"缓存缺失（端点不完整）: {symbol} {interval} "
                    f"缺少: {', '.join(missing)}，创建异步任务"
                )
                # 缓存缺失时，创建异步任务获取数据
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
                # 注意：异步任务返回的 ACK 会被忽略，因为第一阶段已发送
                if result.get("type") == "ACK":
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
                data={
                    "type": "klines",
                    **kline_data.model_dump(),
                },
            )

        # 第三阶段：发送处理结果
        await self._client_manager.send(client_id, result)
        return None

    async def _handle_get_search_symbols(
        self, data: dict[str, Any], request_id: str | None
    ) -> dict[str, Any]:
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
                # 合并结果，现货优先
                symbols = spot_symbols + futures_symbols
                total = len(symbols)
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

            return self._response(
                msg_type="SEARCH_SYMBOLS_DATA",
                request_id=request_id,
                data={
                    "type": "search_symbols",
                    "symbols": symbols,
                    "total": total,
                    "count": len(symbols),
                },
            )
        except Exception as e:
            logger.error(f"搜索交易对失败: {e}")
            return self._error_response(
                error_code="SEARCH_SYMBOLS_FAILED",
                error_message=f"搜索失败: {str(e)}",
            )

    async def _handle_get_resolve_symbol(
        self, data: dict[str, Any], request_id: str | None
    ) -> dict[str, Any]:
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

        try:
            symbol_info = await self._exchange_repo.resolve_symbol(
                symbol=symbol,
                exchange="BINANCE",
                market_type="SPOT",
            )

            return self._response(
                msg_type="SYMBOL_DATA",
                request_id=request_id,
                data={
                    "type": "resolve_symbol",
                    "symbol": symbol_info,
                },
            )
        except Exception as e:
            logger.error(f"解析交易对失败: {e}")
            return self._error_response(
                error_code="RESOLVE_SYMBOL_FAILED",
                error_message=f"解析失败: {str(e)}",
            )

    async def _handle_alert_request(
        self, action: str, data: dict[str, Any], request_id: str | None
    ) -> dict[str, Any]:
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
            "enable": self._alert_handler.handle_enable_alert_config,
            "disable": lambda d, rid: self._alert_handler.handle_enable_alert_config(
                {**d, "is_enabled": False}, rid
            ),
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
    ) -> dict[str, Any]:
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

        logger.info(
            f"客户端 {client_id} 订阅 {len(subscriptions)} 个键，"
            f"新增数据库记录 {inserted_count} 个"
        )

        return self._response(
            msg_type="SUBSCRIPTION_DATA",  # 遵循07-websocket-protocol.md规范
            request_id=request_id,
            data={
                "type": "subscribe",
                "subscriptions": subscriptions,
                "new_entries": inserted_count,
            },
        )

    async def _handle_unsubscribe(
        self, client_id: str, data: dict[str, Any], request_id: str | None = None
    ) -> dict[str, Any]:
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
            logger.info(
                f"客户端 {client_id} 取消全部 {len(deleted_keys)} 个订阅"
            )
            return self._response(
                msg_type="SUBSCRIPTION_DATA",  # 遵循07-websocket-protocol.md规范
                request_id=request_id,
                data={
                    "type": "unsubscribe",
                    "unsubscribed": deleted_keys,
                    "all": True,
                },
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

        logger.info(
            f"客户端 {client_id} 取消 {len(subscriptions)} 个订阅，"
            f"删除数据库记录 {deleted_count} 个"
        )

        return self._response(
            msg_type="SUBSCRIPTION_DATA",  # 遵循07-websocket-protocol.md规范
            request_id=request_id,
            data={
                "type": "unsubscribe",
                "unsubscribed": subscriptions,
                "deleted_entries": deleted_count,
                "all": False,
            },
        )

    def _response(
        self,
        msg_type: str,
        request_id: str | None,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """构建成功响应

        严格遵循07-websocket-protocol.md规范：
        - 使用 type 字段表示数据类型（如 KLINES_DATA, CONFIG_DATA 等）

        Args:
            msg_type: 消息类型（如 KLINES_DATA, CONFIG_DATA, SUBSCRIPTION_DATA 等）
            request_id: 请求 ID
            data: 响应数据

        Returns:
            响应消息字典
        """
        return {
            "protocolVersion": "2.0",
            "type": msg_type,  # 遵循07-websocket-protocol.md规范
            "requestId": request_id,
            "timestamp": self._timestamp(),
            "data": data,
        }

    def _error_response(
        self,
        error_code: str,
        error_message: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """构建错误响应

        严格遵循07-websocket-protocol.md规范：
        - type 字段值为 "ERROR"

        Args:
            error_code: 错误代码
            error_message: 错误信息
            request_id: 请求 ID

        Returns:
            错误响应字典
        """
        return {
            "protocolVersion": "2.0",
            "type": "ERROR",  # 遵循07-websocket-protocol.md规范
            "requestId": request_id,
            "timestamp": self._timestamp(),
            "data": {
                "errorCode": error_code,
                "errorMessage": error_message,
            },
        }

    async def _create_async_task(
        self,
        client_id: str,
        task_type: str,
        payload: dict[str, Any],
        store_result: bool = True,
        request_id: str | None = None,
    ) -> dict[str, Any]:
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
            task_payload = payload.copy()
            if request_id:
                task_payload["requestId"] = request_id

            # 创建任务
            task_id = await self._tasks_repo.create_task(
                task_type=task_type,
                payload=task_payload,
            )

            # 注册任务与客户端的映射（用于推送结果）
            self._client_manager.register_task(task_id, client_id)

            logger.info(
                f"创建异步任务: client_id={client_id}, "
                f"task_type={task_type}, task_id={task_id}, store_result={store_result}"
            )

            # 返回 ack 确认消息（三阶段模式第一阶段）
            # 严格遵循07-websocket-protocol.md规范：type 值为 "ACK"
            # 注意：taskId 不返回给客户端，仅在服务端内部使用
            # data 为空对象，无需额外信息
            return {
                "protocolVersion": "2.0",
                "type": "ACK",  # 遵循07-websocket-protocol.md规范
                "requestId": request_id,
                "timestamp": self._timestamp_ms(),
                "data": {}
            }

        except Exception as e:
            logger.error(f"创建任务失败: {task_type}, {e}")
            return self._error_response(
                error_code="TASK_CREATION_FAILED",
                error_message=f"Failed to create task: {str(e)}",
            )

    def _timestamp(self) -> int:
        """获取当前时间戳（秒）"""
        import time
        return int(time.time())

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
