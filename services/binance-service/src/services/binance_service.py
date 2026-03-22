"""
币安服务主类（新架构）

根据 SUBSCRIPTION_AND_REALTIME_DATA.md 设计，仅支持新架构：
- 一次性请求：get_klines, get_server_time, get_quotes
- 持续订阅：KLINE, QUOTES, TRADE

整合所有组件：
- HTTP客户端：获取历史数据
- WebSocket客户端：订阅实时数据
- 数据存储：写入数据库
- 任务监听：监听 task_new 通知
- 订阅同步：监听 subscription_add/remove/clean 通知，管理币安WS订阅

事件驱动流程：
1. 监听 task_new 频道
2. 收到任务后，根据类型调用对应客户端
3. 将数据写入数据库（触发 realtime_update 通知）
4. 监听 subscription_add/remove/clean 频道，执行币安WS订阅/取消

数据转换流程：
- HTTP响应：原始数据 -> KlineResponse.model_validate() -> KlineCreate
- WS消息：原始数据 -> KlineWebSocket.model_validate() -> realtime_data表
- 归档：trigger_archive_closed_kline 触发器自动归档到 klines_history 表

参考设计文档：QUANT_TRADING_SYSTEM_ARCHITECTURE.md
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import asyncpg
from pydantic import ValidationError

from clients import (
    BinanceSpotHTTPClient,
    BinanceFuturesHTTPClient,
    BinanceSpotWSClient,
    BinanceFuturesWSClient,
    BinanceSpotPrivateHTTPClient,
    BinanceFuturesPrivateHTTPClient,
    BinanceFuturesPrivateWSClient,
    BinanceSpotPrivateWSClient,
    SpotUserStreamClient,
)
from storage import ExchangeInfoRepository
from db.tasks_repository import TasksRepository
from db.realtime_data_repository import RealtimeDataRepository
from db.order_tasks_repository import OrderTasksRepository
from events import TaskListener, TaskPayload
from events.exchange_info_handler import ExchangeInfoHandler
from events.order_task_listener import OrderTaskListener
from ws_subscription_manager import WSSubscriptionManager
from models.kline_models import (
    BinanceSpotKlineGetModel,
    BinanceFuturesKlineGetModel,
)
from models.ticker_models import (
    BinanceSpotTicker24hrGetModel,
    BinanceFuturesTicker24hrGetModel,
)
from models.account_models import (
    BinanceSpotAccountGetModel,
    BinanceFuturesAccountGetModel,
)
from models.internal_models import (
    InternalKlineData,
    InternalQuoteData,
    InternalQuoteValues,
    InternalQuotesResult,
)
from services.order_task_handler import OrderTaskHandler
from utils import resolution_to_interval

logger = logging.getLogger(__name__)


class BinanceService:
    """币安数据采集服务（新架构）

    职责：
    1. 监听数据库任务队列（task_new 频道）
    2. 根据任务类型调用币安客户端
    3. 写入数据库（realtime_update 通知 + 归档触发器）
    4. 订阅同步：监听subscription_add/remove/clean通知，管理币安WS订阅

    任务类型：
    - get_klines: 获取K线历史数据（HTTP）-> klines_history表
    - get_server_time: 获取服务器时间（HTTP）-> tasks.result
    - get_quotes: 获取实时报价（HTTP）-> tasks.result

    配置：
    - CLASH_PROXY_HTTP_URL: HTTP代理地址
    - CLASH_PROXY_WS_URL: WebSocket代理地址
    """

    def __init__(
        self,
        dsn: str,
        proxy_http: Optional[str] = None,
        proxy_ws: Optional[str] = None,
    ) -> None:
        """初始化服务

        Args:
            dsn: 数据库连接字符串
            proxy_http: HTTP代理地址
            proxy_ws: WebSocket代理地址
        """
        self._dsn = dsn
        self._proxy_http = proxy_http
        self._proxy_ws = proxy_ws

        self._pool: Optional[asyncpg.Pool] = None
        self._spot_http: Optional[BinanceSpotHTTPClient] = None
        self._futures_http: Optional[BinanceFuturesHTTPClient] = None
        self._spot_private_http: Optional[BinanceSpotPrivateHTTPClient] = None
        self._futures_private_http: Optional[BinanceFuturesPrivateHTTPClient] = None
        self._spot_ws: Optional[BinanceSpotWSClient] = None
        self._futures_ws: Optional[BinanceFuturesWSClient] = None
        # 私有WebSocket客户端（用于订单功能）
        self._spot_private_ws: Optional[BinanceSpotPrivateWSClient] = None
        self._futures_private_ws: Optional[BinanceFuturesPrivateWSClient] = None
        # 用户数据流客户端（用于账户订阅）
        self._spot_user_stream: Optional[SpotUserStreamClient] = None
        self._exchange_repo: Optional[ExchangeInfoRepository] = None
        self._tasks_repo: Optional[TasksRepository] = None  # Tasks表仓储
        self._realtime_repo: Optional[RealtimeDataRepository] = (
            None  # RealtimeData表仓储
        )
        # 订单任务相关
        self._order_tasks_repo: Optional[OrderTasksRepository] = None
        self._order_task_listener: Optional[OrderTaskListener] = None
        self._order_task_handler: Optional[OrderTaskHandler] = None
        self._task_listener: Optional[TaskListener] = None
        self._exchange_handler: Optional[ExchangeInfoHandler] = None
        self._ws_manager: Optional[WSSubscriptionManager] = None

        self._running = False

    async def start(self) -> None:
        """启动服务"""
        if self._running:
            logger.warning("服务已在运行")
            return

        logger.info("启动币安服务...")

        # 初始化数据库连接池
        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=2,
            max_size=10,
        )

        # 初始化HTTP客户端
        self._spot_http = BinanceSpotHTTPClient(proxy_url=self._proxy_http)
        self._futures_http = BinanceFuturesHTTPClient(proxy_url=self._proxy_http)

        # 初始化私有HTTP客户端（用于账户信息等需要签名的请求）
        # 从环境变量读取 API 密钥和私钥
        api_key = os.environ.get("BINANCE_API_KEY", "")
        signature_type = os.environ.get("BINANCE_SIGNATURE_TYPE", "ed25519")

        # 读取私钥文件
        private_key_pem: bytes = b""
        private_key_path = os.environ.get(
            "BINANCE_PRIVATE_KEY_PATH", "/app/keys/private_key.pem"
        )
        try:
            private_key_pem = Path(private_key_path).read_bytes()
        except FileNotFoundError:
            logger.warning(f"私钥文件不存在: {private_key_path}, 账户信息功能将不可用")

        # 初始化现货私有客户端
        if api_key and private_key_pem:
            self._spot_private_http = BinanceSpotPrivateHTTPClient(
                api_key=api_key,
                private_key_pem=private_key_pem,
                signature_type=signature_type,
                proxy_url=self._proxy_http,
            )
            logger.info("现货私有客户端已初始化")
        else:
            logger.warning("BINANCE_API_KEY 或私钥未配置，现货账户信息功能不可用")
            self._spot_private_http = None

        # 初始化期货私有客户端
        futures_api_key = os.environ.get("BINANCE_FUTURES_API_KEY", api_key)
        futures_private_key_path = os.environ.get(
            "BINANCE_FUTURES_PRIVATE_KEY_PATH", private_key_path
        )
        try:
            private_key_pem = Path(futures_private_key_path).read_bytes()
        except FileNotFoundError:
            logger.warning(
                f"期货私钥文件不存在: {futures_private_key_path}, 期货账户信息功能将不可用"
            )

        if futures_api_key and private_key_pem:
            self._futures_private_http = BinanceFuturesPrivateHTTPClient(
                api_key=futures_api_key,
                private_key_pem=private_key_pem,
                signature_type=signature_type,
                proxy_url=self._proxy_http,
            )
            logger.info("期货私有客户端已初始化")
        else:
            logger.warning(
                "BINANCE_FUTURES_API_KEY 或私钥未配置，期货账户信息功能不可用"
            )
            self._futures_private_http = None

        # 初始化WebSocket客户端
        self._spot_ws = BinanceSpotWSClient(proxy_url=self._proxy_ws)
        self._futures_ws = BinanceFuturesWSClient(proxy_url=self._proxy_ws)

        # 注册断线重连回调（用于全量恢复订阅）
        self._spot_ws.set_reconnect_callback(self._on_ws_reconnect)
        self._futures_ws.set_reconnect_callback(self._on_ws_reconnect)

        # 初始化私有WebSocket客户端（用于订单功能）
        # 从环境变量读取配置
        futures_api_key = os.environ.get("BINANCE_FUTURES_API_KEY", api_key)
        if api_key and private_key_pem:
            # 现货私有WebSocket客户端
            self._spot_private_ws = BinanceSpotPrivateWSClient(
                api_key=api_key,
                private_key_pem=private_key_pem,
                proxy_url=self._proxy_ws,
            )
            logger.info("现货私有WebSocket客户端已初始化")
            # 连接私有WebSocket并进行认证
            try:
                await self._spot_private_ws.connect()
                logger.info("现货私有WebSocket已连接并认证")
            except Exception as e:
                logger.error(f"现货私有WebSocket连接失败: {e}")
                self._spot_private_ws = None
        else:
            logger.warning("现货私有WebSocket客户端未初始化（缺少API Key或私钥）")

        if futures_api_key and private_key_pem:
            # 期货私有WebSocket客户端
            self._futures_private_ws = BinanceFuturesPrivateWSClient(
                api_key=futures_api_key,
                private_key_pem=private_key_pem,
                proxy_url=self._proxy_ws,
            )
            logger.info("期货私有WebSocket客户端已初始化")
            # 连接私有WebSocket并进行认证
            try:
                await self._futures_private_ws.connect()
                logger.info("期货私有WebSocket已连接并认证")
            except Exception as e:
                logger.error(f"期货私有WebSocket连接失败: {e}")
                self._futures_private_ws = None
        else:
            logger.warning("期货私有WebSocket客户端未初始化（缺少API Key或私钥）")

        # 初始化用户数据流客户端（用于账户订阅）
        # SpotUserStreamClient 独立处理 session.logon + userDataStream.subscribe
        if api_key and private_key_pem:
            self._spot_user_stream = SpotUserStreamClient(
                api_key=api_key,
                private_key_pem=private_key_pem,
                proxy_url=self._proxy_ws,
            )
            logger.info("现货用户数据流客户端已初始化")
        else:
            logger.warning("现货用户数据流客户端未初始化（缺少API Key或私钥）")

        # 初始化存储层
        self._exchange_repo = ExchangeInfoRepository(self._pool)
        self._tasks_repo = TasksRepository(self._pool)
        # 订单任务仓储
        self._order_tasks_repo = OrderTasksRepository(self._pool)
        self._realtime_repo = RealtimeDataRepository(self._pool)

        # 初始化交易所信息处理器
        self._exchange_handler = ExchangeInfoHandler(
            spot_http=self._spot_http,
            futures_http=self._futures_http,
            exchange_repo=self._exchange_repo,
        )

        # 初始化任务监听器
        self._task_listener = TaskListener(self._pool)

        # 注册任务处理器（新架构）
        # 新架构（一次性请求任务）
        self._task_listener.register("get_klines", self._handle_get_klines)
        self._task_listener.register("get_server_time", self._handle_get_server_time)
        self._task_listener.register("get_quotes", self._handle_get_quotes)
        # 账户信息任务
        self._task_listener.register(
            "get_futures_account", self._handle_get_futures_account
        )
        self._task_listener.register("get_spot_account", self._handle_get_spot_account)
        # 系统管理任务
        self._task_listener.register(
            "system.fetch_exchange_info", self._handle_sync_exchange_info
        )

        # 启动任务监听
        await self._task_listener.start()

        # 初始化订单任务监听器和处理器（订单功能）
        self._order_task_handler = OrderTaskHandler(
            futures_client=self._futures_private_ws,
            spot_client=self._spot_private_ws,
            futures_http_client=self._futures_private_http,
            spot_http_client=self._spot_private_http,
            order_tasks_repo=self._order_tasks_repo,
        )
        self._order_task_listener = OrderTaskListener(self._pool)

        # 注册订单任务处理器
        self._order_task_listener.register(
            "order.create", self._order_task_handler.handle_task
        )
        self._order_task_listener.register(
            "order.cancel", self._order_task_handler.handle_task
        )
        self._order_task_listener.register(
            "order.query", self._order_task_handler.handle_task
        )
        self._order_task_listener.register(
            "order.modify", self._order_task_handler.handle_task
        )

        # 启动订单任务监听
        await self._order_task_listener.start()
        logger.info("订单任务监听器已启动")

        # 初始化WS订阅管理器
        self._ws_manager = WSSubscriptionManager(self._pool)

        # 注册市场数据WS客户端到订阅管理器
        self._ws_manager.register_client("binance-spot-ws-001", self._spot_ws)
        self._ws_manager.register_client("binance-futures-ws-001", self._futures_ws)

        # 注册用户数据流客户端到订阅管理器（用于账户订阅）
        if self._spot_user_stream:
            self._ws_manager.register_user_stream_client(
                "binance-spot-user-stream-001", self._spot_user_stream
            )
            logger.info("现货用户数据流客户端已注册到WS管理器")

        # 启动WS订阅管理器
        await self._ws_manager.start()

        self._running = True
        logger.info("币安服务已启动")

    async def stop(self) -> None:
        """停止服务"""
        if not self._running:
            return

        logger.info("停止币安服务...")

        # 停止WS订阅管理器
        if self._ws_manager:
            await self._ws_manager.stop()

        # 停止任务监听
        if self._task_listener:
            await self._task_listener.stop()

        # 停止订单任务监听器
        if self._order_task_listener:
            await self._order_task_listener.stop()
            logger.info("订单任务监听器已停止")

        # 断开WebSocket连接
        if self._spot_ws:
            await self._spot_ws.disconnect()
        if self._futures_ws:
            await self._futures_ws.disconnect()
        # 断开私有WebSocket连接
        if self._spot_private_ws:
            await self._spot_private_ws.disconnect()
        if self._futures_private_ws:
            await self._futures_private_ws.disconnect()

        # 关闭HTTP客户端
        if self._spot_http:
            await self._spot_http.close()
        if self._futures_http:
            await self._futures_http.close()
        if self._spot_private_http:
            await self._spot_private_http.close()
        if self._futures_private_http:
            await self._futures_private_http.close()

        # 关闭连接池
        if self._pool:
            await self._pool.close()

        self._running = False
        logger.info("币安服务已停止")

    async def _on_ws_reconnect(self) -> None:
        """WS断线重连回调

        触发全量同步恢复订阅。
        """
        logger.info("开始全量恢复订阅...")

        if not self._ws_manager:
            logger.warning("WSSubscriptionManager未初始化，无法恢复订阅")
            return

        # 调用全量同步
        await self._ws_manager.full_sync()

    async def _handle_sync_exchange_info(self, payload: TaskPayload) -> None:
        """处理同步交易所信息任务

        从币安API获取交易所信息并存储到数据库。
        支持新旧两种 payload 格式。
        完成后更新任务状态为 COMPLETED 或 FAILED。
        """
        task_id = payload.task_id

        if not self._exchange_handler:
            logger.error("交易所信息处理器未初始化")
            if task_id and self._tasks_repo:
                await self._tasks_repo.fail(task_id, "交易所信息处理器未初始化")
            return

        # 标记任务为处理中
        if task_id and self._tasks_repo:
            await self._tasks_repo.set_processing(task_id)

        # 解析参数
        import json as json_module

        params = {}
        if payload.payload:
            try:
                params = (
                    json_module.loads(payload.payload)
                    if isinstance(payload.payload, str)
                    else payload.payload
                )
            except json_module.JSONDecodeError:
                pass

        try:
            await self._exchange_handler.handle_fetch_exchange_info(
                action=payload.task_type,
                resource=payload.symbol,
                params=params,
            )
            # 任务成功完成
            if task_id and self._tasks_repo:
                await self._tasks_repo.complete(task_id, None)
        except Exception as e:
            logger.error(f"同步交易所信息失败: {e}")
            if task_id and self._tasks_repo:
                # 对 ValidationError 进行截断，避免 payload 超过 PostgreSQL NOTIFY 限制
                error_msg = str(e)
                if isinstance(e, ValidationError):
                    # 只保留前 500 个字符和错误数量摘要
                    error_count = len(e.errors())
                    error_msg = f"ValidationError ({error_count} errors): {error_msg[:500]}..."
                # result 字段限制在 2000 字符以内
                await self._tasks_repo.fail(task_id, error_msg[:2000])

    async def run(self) -> None:
        """运行服务（阻塞）"""
        await self.start()

        try:
            # 保持运行
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    # ========== 新架构任务处理器 ==========

    async def _handle_get_klines(self, payload: TaskPayload) -> None:
        """处理获取K线历史数据请求（新架构）

        循环获取时间范围内的所有K线数据：
        1. 每次获取1000条（币安API最大值）
        2. 使用 close_time + 1ms 自动循环获取下一批
        3. 写入 klines_history 表
        4. 完成任务，result=None

        Args:
            payload: 任务载荷，包含 symbol, interval, from_time, to_time
        """
        task_id = payload.task_id
        if not task_id or not self._tasks_repo:
            logger.error("任务ID或TasksRepository未初始化")
            return

        # 解析参数
        params = self._parse_task_params(payload)
        symbol = params.get("symbol", "")
        interval = params.get(
            "interval", "60"
        )  # 使用 interval，与数据库和API网关保持一致
        from_time = params.get("from_time")
        to_time = params.get("to_time")

        logger.info(
            f"获取K线历史数据: {symbol} {interval} {from_time}-{to_time} (task_id={task_id})"
        )

        # 标记任务为处理中
        await self._tasks_repo.set_processing(task_id)

        try:
            # 解析交易对
            clean_symbol = self._parse_symbol(symbol)

            # 判断是现货还是期货
            is_futures = clean_symbol.endswith(".PERP")
            if is_futures:
                pair = clean_symbol.replace(".PERP", "")
                http_client = self._futures_http
            else:
                pair = clean_symbol.upper()
                http_client = self._spot_http

            # 检查 HTTP 客户端是否初始化
            if http_client is None:
                logger.error(f"HTTP客户端未初始化: {symbol}")
                await self._tasks_repo.set_failed(task_id, "HTTP客户端未初始化")
                return

            # 转换间隔格式
            interval_str = resolution_to_interval(interval)

            # 循环获取所有K线数据
            all_raw_klines = []
            current_start_time = from_time
            max_limit = 1000  # 币安API最大限制

            # 判断是否需要循环：如果指定了 from_time 或 to_time，则需要循环获取
            # 如果两者都为空，API会返回最近的K线数据，只需请求一次
            need_loop = from_time is not None or to_time is not None

            while True:
                # 获取下一批K线数据
                batch_klines = await http_client.get_klines(
                    symbol=pair,
                    interval=interval_str,
                    limit=max_limit,
                    start_time=current_start_time,
                    end_time=to_time,
                )

                if not batch_klines:
                    # 没有更多数据，退出循环
                    break

                all_raw_klines.extend(batch_klines)
                logger.debug(f"获取批次: {len(batch_klines)} 条")

                # 不需要循环的情况（from_time 和 to_time 都为空）
                # API会自动返回最近的K线数据，只需请求一次
                if not need_loop:
                    break

                # 检查是否已获取完整个时间范围
                if len(batch_klines) < max_limit:
                    # 不足1000条，说明已到达范围末尾
                    break

                # 使用最后一条的 close_time + 1ms 获取下一批（避免重复）
                last_close_time = batch_klines[-1][6]  # close_time 是第7个字段（索引6）
                current_start_time = last_close_time + 1

                # 如果指定了 to_time 且起始时间已超过，退出循环
                if to_time is not None and current_start_time > to_time:
                    break

            # 转换数据格式
            kline_model_class = (
                BinanceFuturesKlineGetModel if is_futures else BinanceSpotKlineGetModel
            )
            klines = []
            for raw_kline in all_raw_klines:
                kline = self._convert_kline_to_internal(
                    raw_kline, symbol, interval, kline_model_class
                )
                klines.append(kline)

            # 直接写入 klines_history 表（使用 TradingView 格式）
            if self._pool:
                await self._insert_klines_to_history(
                    symbol, interval, all_raw_klines, is_futures=is_futures
                )
            else:
                logger.warning(f"pool 未初始化，跳过写入: {symbol} {interval}")

            # 完成任务，result=None（不存储大数据）
            # api-service 收到通知后会查询 klines_history 表获取数据
            await self._tasks_repo.complete(task_id, None)

            logger.info(f"K线数据获取完成: {symbol} {interval} 共 {len(klines)} 条")

        except Exception as e:
            logger.error(f"获取K线历史数据失败: {e}")
            await self._tasks_repo.fail(task_id, str(e))

    async def _handle_get_server_time(self, payload: TaskPayload) -> None:
        """处理获取服务器时间请求（新架构）

        Args:
            payload: 任务载荷
        """
        task_id = payload.task_id
        if not task_id or not self._tasks_repo:
            logger.error("任务ID或TasksRepository未初始化")
            return

        logger.info(f"获取服务器时间 (task_id={task_id})")

        # 检查 HTTP 客户端是否初始化
        if self._spot_http is None:
            logger.error("现货HTTP客户端未初始化")
            await self._tasks_repo.set_failed(task_id, "HTTP客户端未初始化")
            return

        # 标记任务为处理中
        await self._tasks_repo.set_processing(task_id)

        try:
            # 获取服务器时间（使用现货HTTP客户端）
            server_time = await self._spot_http.get_server_time()

            # 写入任务结果
            result = {
                "server_time": server_time,
                "iso_time": datetime.fromtimestamp(
                    server_time / 1000, tz=timezone.utc
                ).isoformat(),
            }
            await self._tasks_repo.complete(task_id, result)

            logger.info(f"服务器时间获取完成: {server_time}")

        except Exception as e:
            logger.error(f"获取服务器时间失败: {e}")
            await self._tasks_repo.fail(task_id, str(e))

    async def _handle_get_quotes(self, payload: TaskPayload) -> None:
        """处理获取实时报价请求（新架构）- 批量优化版本

        数据流程：
        1. 按现货/期货分组symbols
        2. 现货使用批量API一次获取（symbols参数）
        3. 期货使用并发请求（asyncio.gather）
        4. 合并结果，一次性写入任务表

        Args:
            payload: 任务载荷，包含 symbols 列表
        """
        task_id = payload.task_id
        if not task_id or not self._tasks_repo:
            logger.error("任务ID或TasksRepository未初始化")
            return

        # 解析参数
        params = self._parse_task_params(payload)
        symbols = params.get("symbols", [])

        logger.info(f"获取实时报价: {symbols} (task_id={task_id})")

        # 标记任务为处理中
        await self._tasks_repo.set_processing(task_id)

        try:
            # ========== 第一步：按现货/期货分组 ==========
            spot_symbols: list[str] = []  # 现货交易对（不带前缀）
            spot_symbols_original: list[str] = []  # 原始symbol（带前缀）
            futures_symbols: list[str] = []  # 期货交易对（不带前缀）
            futures_symbols_original: list[str] = []  # 原始symbol

            for symbol in symbols:
                clean_symbol = self._parse_symbol(symbol)
                is_futures = clean_symbol.endswith(".PERP")

                if is_futures:
                    pair = clean_symbol.replace(".PERP", "")
                    futures_symbols.append(pair)
                    futures_symbols_original.append(symbol)
                else:
                    spot_symbols.append(clean_symbol.upper())
                    spot_symbols_original.append(symbol)

            # ========== 第二步：批量获取数据（直接分离来源）==========
            spot_raw_tickers: list[dict] = []  # 直接分离，避免依赖symbol值区分
            futures_raw_tickers: list[dict] = []

            # 现货：使用批量API（一次请求）
            if spot_symbols:
                if self._spot_http is None:
                    logger.error("现货HTTP客户端未初始化")
                    await self._tasks_repo.set_failed(task_id, "HTTP客户端未初始化")
                    return
                logger.info(f"批量获取现货ticker: {spot_symbols}")
                spot_tickers = await self._spot_http.get_24hr_ticker(
                    symbols=spot_symbols
                )
                # spot_tickers 可能是单个dict（1个symbol）或list（多个symbol）
                if isinstance(spot_tickers, list):
                    spot_raw_tickers.extend(spot_tickers)
                else:
                    spot_raw_tickers.append(spot_tickers)

            # 期货：使用并发请求（期货API不支持批量symbols参数）
            if futures_symbols:
                if self._futures_http is None:
                    logger.error("期货HTTP客户端未初始化")
                    await self._tasks_repo.set_failed(task_id, "HTTP客户端未初始化")
                    return
                logger.info(f"并发获取期货ticker: {futures_symbols}")
                futures_tickers = await self._futures_http.get_24hr_ticker(
                    symbols=futures_symbols
                )
                # futures_tickers 已经是list
                if isinstance(futures_tickers, list):
                    futures_raw_tickers.extend(futures_tickers)
                else:
                    futures_raw_tickers.append(futures_tickers)

            # ========== 第三步：转换为统一格式 ==========
            # 创建 symbol -> original symbol 的映射
            symbol_mapping: dict[str, str] = {}
            for i, s in enumerate(spot_symbols):
                symbol_mapping[s] = spot_symbols_original[i]
            for i, s in enumerate(futures_symbols):
                symbol_mapping[s] = futures_symbols_original[i]

            quotes = []

            # 处理现货 ticker：使用 BinanceSpotTicker24hrGetModel 验证
            for raw_ticker in spot_raw_tickers:
                ticker_symbol = raw_ticker.get("symbol", "")
                original_symbol = symbol_mapping.get(
                    ticker_symbol, f"BINANCE:{ticker_symbol}"
                )

                # 使用现货 ticker 模型验证数据
                ticker = BinanceSpotTicker24hrGetModel.model_validate(raw_ticker)

                # 转换为内部报价格式
                quote = InternalQuoteData(
                    n=original_symbol,
                    s="ok",
                    v=InternalQuoteValues(
                        lp=float(ticker.last_price),
                        ch=float(ticker.price_change),
                        chp=float(ticker.price_change_percent),
                        high=float(ticker.high_price),
                        low=float(ticker.low_price),
                        volume=float(ticker.volume),
                        quote_volume=float(ticker.quote_volume),
                        timestamp=ticker.close_time,
                    ),
                )
                quotes.append(quote)

            # 处理期货 ticker：使用 BinanceFuturesTicker24hrGetModel 验证
            for raw_ticker in futures_raw_tickers:
                ticker_symbol = raw_ticker.get("symbol", "")
                original_symbol = symbol_mapping.get(
                    ticker_symbol, f"BINANCE:{ticker_symbol}"
                )

                # 使用期货 ticker 模型验证数据
                ticker = BinanceFuturesTicker24hrGetModel.model_validate(raw_ticker)

                # 转换为内部报价格式
                quote = InternalQuoteData(
                    n=original_symbol,
                    s="ok",
                    v=InternalQuoteValues(
                        lp=float(ticker.last_price),
                        ch=float(ticker.price_change),
                        chp=float(ticker.price_change_percent),
                        high=float(ticker.high_price),
                        low=float(ticker.low_price),
                        volume=float(ticker.volume),
                        quote_volume=float(ticker.quote_volume),
                        timestamp=ticker.close_time,
                    ),
                )
                quotes.append(quote)

            # ========== 第四步：一次性写入任务结果 ==========
            result = InternalQuotesResult(quotes=quotes, count=len(quotes))
            await self._tasks_repo.complete(task_id, result.model_dump(mode='json'))

            logger.info(f"实时报价获取完成: 共 {len(quotes)} 个交易对")

        except Exception as e:
            logger.error(f"获取实时报价失败: {e}")
            await self._tasks_repo.fail(task_id, str(e))

    async def _handle_get_futures_account(self, payload: TaskPayload) -> None:
        """处理获取期货账户信息请求

        流程：
        1. 获取账户信息
        2. 写入 account_info 表（保存原始数据）
        3. 更新 tasks.status = completed（result 为 None）

        Args:
            payload: 任务载荷
        """
        task_id = payload.task_id
        if not task_id or not self._tasks_repo:
            logger.error("任务ID或TasksRepository未初始化")
            return

        # 检查期货私有客户端是否已初始化
        if not self._futures_private_http:
            logger.error(
                "期货私有客户端未初始化，请配置 BINANCE_FUTURES_API_KEY 和私钥"
            )
            await self._tasks_repo.fail(task_id, "期货账户功能未配置，请联系管理员")
            return

        logger.info(f"获取期货账户信息 (task_id={task_id})")

        # 标记任务为处理中
        await self._tasks_repo.set_processing(task_id)

        try:
            # 获取期货账户信息（使用私有客户端，返回原始 dict）
            account_info_dict = await self._futures_private_http.get_account_info()

            # 服务层负责将 dict 转换为 Pydantic 模型
            account_info = BinanceFuturesAccountGetModel.model_validate(account_info_dict)

            # 转换为字典格式，使用 mode='json' 自动处理 Decimal/ datetime 序列化
            account_data = account_info.model_dump(mode='json')

            # 获取更新时间（V3 API 在 assets[0] 中返回 updateTime）
            update_time = (
                account_info.assets[0].update_time
                if account_info.assets and account_info.assets[0].update_time
                else None
            )

            # 写入 account_info 表（保存原始数据，前端自行解析）
            await self._tasks_repo.save_account_info(
                account_type="FUTURES",
                data=account_data,
                update_time=update_time,
            )

            # 更新任务状态为 completed（result 为 None，通过 account_info 表传递数据）
            await self._tasks_repo.complete(task_id, None)

            logger.info("期货账户信息获取完成，已写入 account_info 表")

        except Exception as e:
            logger.error(f"获取期货账户信息失败: {e}")
            await self._tasks_repo.fail(task_id, str(e))

    async def _handle_get_spot_account(self, payload: TaskPayload) -> None:
        """处理获取现货账户信息请求

        流程：
        1. 获取账户信息
        2. 写入 account_info 表（保存原始数据）
        3. 更新 tasks.status = completed（result 为 None）

        Args:
            payload: 任务载荷
        """
        task_id = payload.task_id
        if not task_id or not self._tasks_repo:
            logger.error("任务ID或TasksRepository未初始化")
            return

        # 检查现货私有客户端是否已初始化
        if not self._spot_private_http:
            logger.error("现货私有客户端未初始化，请配置 BINANCE_API_KEY 和私钥")
            await self._tasks_repo.fail(task_id, "现货账户功能未配置，请联系管理员")
            return

        logger.info(f"获取现货账户信息 (task_id={task_id})")

        # 标记任务为处理中
        await self._tasks_repo.set_processing(task_id)

        try:
            # 获取现货账户信息（使用私有客户端，返回原始 dict）
            account_info_dict = await self._spot_private_http.get_account_info()

            # 服务层负责将 dict 转换为 Pydantic 模型
            account_info = BinanceSpotAccountGetModel.model_validate(account_info_dict)

            # 转换为字典格式，使用 mode='json' 自动处理 Decimal/ datetime 序列化
            account_data = account_info.model_dump(mode='json')

            # 获取更新时间
            update_time = account_info.update_time

            # 写入 account_info 表（保存原始数据，前端自行解析）
            await self._tasks_repo.save_account_info(
                account_type="SPOT",
                data=account_data,
                update_time=update_time,
            )

            # 更新任务状态为 completed（result 为 None，通过 account_info 表传递数据）
            await self._tasks_repo.complete(task_id, None)

            logger.info("现货账户信息获取完成，已写入 account_info 表")

        except Exception as e:
            logger.error(f"获取现货账户信息失败: {e}")
            await self._tasks_repo.fail(task_id, str(e))

    # ========== 辅助方法 ==========

    def _parse_task_params(self, payload: TaskPayload) -> dict:
        """解析任务载荷参数

        Args:
            payload: 任务载荷

        Returns:
            参数字典
        """
        # 尝试解析 JSON 格式的 payload
        if payload.payload:
            try:
                import json as json_module

                params = (
                    json_module.loads(payload.payload)
                    if isinstance(payload.payload, str)
                    else payload.payload
                )
                return params if isinstance(params, dict) else {}
            except Exception as e:
                logger.warning(f"解析payload失败: {e}")
        return {}

    def _parse_symbol(self, symbol: str) -> str:
        """解析交易对符号

        Args:
            symbol: 原始符号，可能包含前缀

        Returns:
            干净的符号
        """
        if symbol.startswith("BINANCE:"):
            return symbol.replace("BINANCE:", "")
        return symbol

    def _convert_kline_to_internal(
        self,
        raw_kline: list,
        symbol: str,
        interval: str,
        kline_model_class: type["BinanceSpotKlineGetModel | BinanceFuturesKlineGetModel"],
    ) -> InternalKlineData:
        """将原始K线数据转换为内部数据模型

        Args:
            raw_kline: 原始K线数据（12字段数组）
            symbol: 交易对符号（带 BINANCE: 前缀）
            interval: K线间隔
            kline_model_class: K线模型类（BinanceSpotKlineGetModel 或 BinanceFuturesKlineGetModel）

        Returns:
            内部K线数据模型
        """
        # 将数组转换为字典格式供 Pydantic 模型验证
        kline_dict = {str(i): v for i, v in enumerate(raw_kline)}
        kline_model = kline_model_class.model_validate(kline_dict)

        # 转换为内部数据模型
        return InternalKlineData(
            time=kline_model.open_time,
            close_time=kline_model.close_time,
            open=float(kline_model.open_price),
            high=float(kline_model.high_price),
            low=float(kline_model.low_price),
            close=float(kline_model.close_price),
            volume=float(kline_model.volume),
            quote_volume=float(kline_model.quote_volume),
            number_of_trades=kline_model.number_of_trades,
            taker_buy_base_volume=float(kline_model.taker_buy_base_volume),
            taker_buy_quote_volume=float(kline_model.taker_buy_quote_volume),
            symbol=symbol,
            interval=interval,
        )

    async def _insert_klines_to_history(
        self,
        symbol: str,
        interval: str,
        raw_klines: list,
        is_futures: bool = False,
    ) -> int:
        """将K线数据写入 klines_history 表

        用于 get_klines 任务，历史数据写入历史表。
        使用 BinanceSpotKlineGetModel 或 BinanceFuturesKlineGetModel 验证原始数据。

        Args:
            symbol: 交易对符号（带 BINANCE: 前缀）
            interval: K线间隔
            raw_klines: 原始K线数据列表（12字段数组）
            is_futures: 是否为期货数据

        Returns:
            写入的记录数
        """
        if not raw_klines:
            return 0

        # 根据类型选择模型
        kline_model_class = (
            BinanceFuturesKlineGetModel if is_futures else BinanceSpotKlineGetModel
        )

        # 直接使用 interval（TradingView 格式，如 "1D", "60", "M"）
        query = """
            INSERT INTO klines_history (
                symbol, interval, open_time, close_time,
                open_price, high_price, low_price, close_price,
                volume, quote_volume, number_of_trades,
                taker_buy_base_volume, taker_buy_quote_volume
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
            )
            ON CONFLICT (symbol, open_time, interval) DO UPDATE SET
                close_time = EXCLUDED.close_time,
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume,
                quote_volume = EXCLUDED.quote_volume,
                number_of_trades = EXCLUDED.number_of_trades,
                taker_buy_base_volume = EXCLUDED.taker_buy_base_volume,
                taker_buy_quote_volume = EXCLUDED.taker_buy_quote_volume
        """

        async with self._pool.acquire() as conn:
            inserted_count = 0
            error_count = 0
            for i, raw_kline in enumerate(raw_klines):
                try:
                    # 使用内部数据模型转换和验证
                    kline = self._convert_kline_to_internal(
                        raw_kline, symbol, interval, kline_model_class
                    )

                    await conn.execute(
                        query,
                        symbol,
                        interval,
                        datetime.fromtimestamp(
                            kline.time / 1000, tz=timezone.utc
                        ),
                        datetime.fromtimestamp(
                            kline.close_time / 1000, tz=timezone.utc
                        ),
                        kline.open,
                        kline.high,
                        kline.low,
                        kline.close,
                        kline.volume,
                        kline.quote_volume,
                        kline.number_of_trades,
                        kline.taker_buy_base_volume,
                        kline.taker_buy_quote_volume,
                    )
                    inserted_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(
                        f"写入第 {i} 条K线失败: {symbol} {interval} open_time={raw_kline[0]}, error={e}"
                    )

        logger.debug(
            f"已写入 {inserted_count}/{len(raw_klines)} 条K线到 klines_history: {symbol} {interval} (errors={error_count})"
        )
        return inserted_count

    async def _write_realtime_data(
        self,
        subscription_key: str,
        data_type: str,
        data: dict,
        event_time: Optional[str] = None,
    ) -> None:
        """写入实时数据到 realtime_data 表

        触发 realtime_update 通知，通知API网关数据已更新。

        Args:
            subscription_key: 订阅键
            data_type: 数据类型（KLINE, QUOTES, TRADE）
            data: 实时数据
            event_time: 事件时间（可选）
        """
        if not self._realtime_repo:
            logger.warning("RealtimeDataRepository未初始化")
            return

        try:
            await self._realtime_repo.update_data(subscription_key, data, event_time)
            logger.debug(f"已写入实时数据: {subscription_key} ({data_type})")
        except Exception as e:
            logger.error(f"写入实时数据失败: {e}")
