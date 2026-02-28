"""
币安服务主类（新架构）

根据 SUBSCRIPTION_AND_REALTIME_DATA.md 设计，仅支持新架构：
- 一次性请求：get_klines, get_server_time, get_quotes
- 持续订阅：KLINE, QUOTES, TRADE

整合所有组件：
- HTTP客户端：获取历史数据
- WebSocket客户端：订阅实时数据
- 数据存储：写入数据库
- 任务监听：监听 task.new 通知
- 订阅同步：监听 subscription_add/remove/clean 通知，管理币安WS订阅

事件驱动流程：
1. 监听 task.new 频道
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

from clients import (
    BinanceSpotHTTPClient,
    BinanceFuturesHTTPClient,
    BinanceSpotWSClient,
    BinanceFuturesWSClient,
    BinanceSpotPrivateHTTPClient,
    BinanceFuturesPrivateHTTPClient,
)
from clients.base_ws_client import WSDataPackage
from storage import ExchangeInfoRepository
from db.tasks_repository import TasksRepository
from db.realtime_data_repository import RealtimeDataRepository
from events import TaskListener, TaskPayload
from events.exchange_info_handler import ExchangeInfoHandler
from ws_subscription_manager import WSSubscriptionManager
from models import KlineResponse, KlineWebSocket, Ticker24hrSpot, Ticker24hrFutures
from services.account_subscription_service import AccountSubscriptionService

logger = logging.getLogger(__name__)


from utils import resolution_to_interval


class BinanceService:
    """币安数据采集服务（新架构）

    职责：
    1. 监听数据库任务队列（task.new 频道）
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
        self._exchange_repo: Optional[ExchangeInfoRepository] = None
        self._tasks_repo: Optional[TasksRepository] = None  # Tasks表仓储
        self._realtime_repo: Optional[RealtimeDataRepository] = None  # RealtimeData表仓储
        self._task_listener: Optional[TaskListener] = None
        self._exchange_handler: Optional[ExchangeInfoHandler] = None
        self._ws_manager: Optional[WSSubscriptionManager] = None
        self._account_subscription: Optional[AccountSubscriptionService] = None  # 账户订阅服务

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
        private_key_path = os.environ.get("BINANCE_PRIVATE_KEY_PATH", "/app/keys/private_key.pem")
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
        futures_private_key_path = os.environ.get("BINANCE_FUTURES_PRIVATE_KEY_PATH", private_key_path)
        try:
            private_key_pem = Path(futures_private_key_path).read_bytes()
        except FileNotFoundError:
            logger.warning(f"期货私钥文件不存在: {futures_private_key_path}, 期货账户信息功能将不可用")

        if futures_api_key and private_key_pem:
            self._futures_private_http = BinanceFuturesPrivateHTTPClient(
                api_key=futures_api_key,
                private_key_pem=private_key_pem,
                signature_type=signature_type,
                proxy_url=self._proxy_http,
            )
            logger.info("期货私有客户端已初始化")
        else:
            logger.warning("BINANCE_FUTURES_API_KEY 或私钥未配置，期货账户信息功能不可用")
            self._futures_private_http = None

        # 初始化WebSocket客户端
        self._spot_ws = BinanceSpotWSClient(proxy_url=self._proxy_ws)
        self._futures_ws = BinanceFuturesWSClient(proxy_url=self._proxy_ws)

        # 注册断线重连回调（用于全量恢复订阅）
        self._spot_ws.set_reconnect_callback(self._on_ws_reconnect)
        self._futures_ws.set_reconnect_callback(self._on_ws_reconnect)

        # 初始化存储层
        self._exchange_repo = ExchangeInfoRepository(self._pool)
        self._tasks_repo = TasksRepository(self._pool)
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
        self._task_listener.register("get_futures_account", self._handle_get_futures_account)
        self._task_listener.register("get_spot_account", self._handle_get_spot_account)
        # 系统管理任务
        self._task_listener.register("system.fetch_exchange_info", self._handle_sync_exchange_info)

        # 启动任务监听
        await self._task_listener.start()

        # 初始化WS订阅管理器
        self._ws_manager = WSSubscriptionManager(self._pool)

        # 注册WS客户端到订阅管理器
        self._ws_manager.register_client("binance-spot-ws-001", self._spot_ws)
        self._ws_manager.register_client("binance-futures-ws-001", self._futures_ws)

        # 启动WS订阅管理器
        await self._ws_manager.start()

        # 启动账户订阅服务（如果有 API Key 配置）
        # TODO: 暂时禁用账户订阅服务
        # snapshot_interval = int(os.environ.get("ACCOUNT_SNAPSHOT_INTERVAL", "300"))
        # if api_key and private_key_pem:
        #     futures_api_key = os.environ.get("BINANCE_FUTURES_API_KEY", api_key)
        #     self._account_subscription = AccountSubscriptionService(...)
        #     await self._account_subscription.start()
        logger.info("账户订阅服务已禁用")

        self._running = True
        logger.info("币安服务已启动")

    async def stop(self) -> None:
        """停止服务"""
        if not self._running:
            return

        logger.info("停止币安服务...")

        # 停止账户订阅服务
        if self._account_subscription:
            await self._account_subscription.stop()
            self._account_subscription = None

        # 停止WS订阅管理器
        if self._ws_manager:
            await self._ws_manager.stop()

        # 停止任务监听
        if self._task_listener:
            await self._task_listener.stop()

        # 断开WebSocket连接
        if self._spot_ws:
            await self._spot_ws.disconnect()
        if self._futures_ws:
            await self._futures_ws.disconnect()

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

    def _http_to_kline_create(
        self,
        raw_kline: list,
        symbol: str,
        interval: str,
    ) -> KlineCreate:
        """将HTTP原始数据转换为 KlineCreate

        Args:
            raw_kline: 原始K线数据（12字段数组）
            symbol: 交易对符号
            interval: K线间隔

        Returns:
            KlineCreate 实例
        """
        # 使用 KlineResponse 进行数据验证
        kline_response = KlineResponse.model_validate({
            "0": raw_kline[0],
            "1": raw_kline[1],
            "2": raw_kline[2],
            "3": raw_kline[3],
            "4": raw_kline[4],
            "5": raw_kline[5],
            "6": raw_kline[6],
            "7": raw_kline[7],
            "8": raw_kline[8],
            "9": raw_kline[9],
            "10": raw_kline[10],
            "11": raw_kline[11],
        })

        return KlineCreate(
            symbol=symbol,
            interval=interval,
            open_time=kline_response.open_time,
            close_time=kline_response.close_time,
            open_price=kline_response.open_price,
            high_price=kline_response.high_price,
            low_price=kline_response.low_price,
            close_price=kline_response.close_price,
            volume=kline_response.volume,
            quote_volume=kline_response.quote_volume,
            number_of_trades=kline_response.number_of_trades,
            taker_buy_base_volume=kline_response.taker_buy_base_volume,
            taker_buy_quote_volume=kline_response.taker_buy_quote_volume,
            is_closed=True,  # 历史K线已收盘
        )

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
                params = json_module.loads(payload.payload) if isinstance(payload.payload, str) else payload.payload
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
                await self._tasks_repo.fail(task_id, str(e))

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
        interval = params.get("interval", "60")  # 使用 interval，与数据库和API网关保持一致
        from_time = params.get("from_time")
        to_time = params.get("to_time")

        logger.info(f"获取K线历史数据: {symbol} {interval} {from_time}-{to_time} (task_id={task_id})")

        # 标记任务为处理中
        await self._tasks_repo.set_processing(task_id)

        try:
            # 解析交易对
            clean_symbol = self._parse_symbol(symbol)

            # 判断是现货还是期货
            if clean_symbol.endswith(".PERP"):
                pair = clean_symbol.replace(".PERP", "")
                http_client = self._futures_http
            else:
                pair = clean_symbol.upper()
                http_client = self._spot_http

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
            klines = []
            for raw_kline in all_raw_klines:
                kline = self._convert_kline_to_dict(raw_kline, symbol, interval)
                klines.append(kline)

            # 直接写入 klines_history 表（使用 TradingView 格式）
            if self._pool:
                inserted_count = await self._insert_klines_to_history(symbol, interval, all_raw_klines)
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

        # 标记任务为处理中
        await self._tasks_repo.set_processing(task_id)

        try:
            # 获取服务器时间（使用现货HTTP客户端）
            server_time = await self._spot_http.get_server_time()

            # 写入任务结果
            result = {
                "server_time": server_time,
                "iso_time": datetime.fromtimestamp(server_time / 1000, tz=timezone.utc).isoformat(),
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

            # ========== 第二步：批量获取数据 ==========
            raw_tickers: list[dict] = []

            # 现货：使用批量API（一次请求）
            if spot_symbols:
                logger.info(f"批量获取现货ticker: {spot_symbols}")
                spot_tickers = await self._spot_http.get_24hr_ticker(symbols=spot_symbols)
                # spot_tickers 可能是单个dict（1个symbol）或list（多个symbol）
                if isinstance(spot_tickers, list):
                    raw_tickers.extend(spot_tickers)
                else:
                    raw_tickers.append(spot_tickers)

            # 期货：使用并发请求（期货API不支持批量symbols参数）
            if futures_symbols:
                logger.info(f"并发获取期货ticker: {futures_symbols}")
                futures_tickers = await self._futures_http.get_24hr_ticker(symbols=futures_symbols)
                # futures_tickers 已经是list
                if isinstance(futures_tickers, list):
                    raw_tickers.extend(futures_tickers)
                else:
                    raw_tickers.append(futures_tickers)

            # ========== 第三步：转换为统一格式 ==========
            # 创建 symbol -> original symbol 的映射
            symbol_mapping: dict[str, str] = {}
            for i, s in enumerate(spot_symbols):
                symbol_mapping[s] = spot_symbols_original[i]
            for i, s in enumerate(futures_symbols):
                symbol_mapping[s] = futures_symbols_original[i]

            quotes = []
            for raw_ticker in raw_tickers:
                # 获取交易对名称
                ticker_symbol = raw_ticker.get("symbol", "")
                original_symbol = symbol_mapping.get(ticker_symbol, f"BINANCE:{ticker_symbol}")

                # 使用模型验证数据
                ticker = Ticker24hrSpot.model_validate(raw_ticker)

                # 转换为 TradingView 格式
                quote = {
                    "n": original_symbol,
                    "s": "ok",
                    "v": {
                        "lp": float(ticker.last_price),
                        "ch": float(ticker.price_change),
                        "chp": float(ticker.price_change_percent),
                        "high": float(ticker.high_price),
                        "low": float(ticker.low_price),
                        "volume": float(ticker.volume),
                        "quote_volume": float(ticker.quote_volume),
                        "timestamp": ticker.close_time,
                    },
                }
                quotes.append(quote)

            # ========== 第四步：一次性写入任务结果 ==========
            result = {
                "quotes": quotes,
                "count": len(quotes),
            }
            await self._tasks_repo.complete(task_id, result)

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
            logger.error("期货私有客户端未初始化，请配置 BINANCE_FUTURES_API_KEY 和私钥")
            await self._tasks_repo.fail(task_id, "期货账户功能未配置，请联系管理员")
            return

        logger.info(f"获取期货账户信息 (task_id={task_id})")

        # 标记任务为处理中
        await self._tasks_repo.set_processing(task_id)

        try:
            # 获取期货账户信息（使用私有客户端）
            account_info = await self._futures_private_http.get_account_info()

            # 转换为字典格式
            account_data = account_info.model_dump()

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

            logger.info(f"期货账户信息获取完成，已写入 account_info 表")

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
            # 获取现货账户信息（使用私有客户端）
            account_info = await self._spot_private_http.get_account_info()

            # 转换为字典格式
            account_data = account_info.model_dump()

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

            logger.info(f"现货账户信息获取完成，已写入 account_info 表")

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
                params = json_module.loads(payload.payload) if isinstance(payload.payload, str) else payload.payload
                return params if isinstance(params, dict) else {}
            except Exception:
                pass
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

    def _convert_kline_to_dict(self, raw_kline: list, symbol: str, interval: str) -> dict:
        """将原始K线数据转换为字典格式

        Args:
            raw_kline: 原始K线数据（12字段数组）
            symbol: 交易对符号
            interval: K线间隔

        Returns:
            转换后的字典
        """
        return {
            "time": int(raw_kline[0]),
            "open": float(raw_kline[1]),
            "high": float(raw_kline[2]),
            "low": float(raw_kline[3]),
            "close": float(raw_kline[4]),
            "volume": float(raw_kline[5]),
            "symbol": symbol,
            "interval": interval,
        }

    async def _insert_klines_to_history(
        self,
        symbol: str,
        interval: str,
        raw_klines: list,
    ) -> int:
        """将K线数据写入 klines_history 表

        用于 get_klines 任务，历史数据写入历史表。

        Args:
            symbol: 交易对符号（带 BINANCE: 前缀）
            interval: K线间隔
            raw_klines: 原始K线数据列表

        Returns:
            写入的记录数
        """
        if not raw_klines:
            return 0

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
                    await conn.execute(
                        query,
                        symbol,
                        interval,
                        datetime.fromtimestamp(int(float(raw_kline[0])) / 1000, tz=timezone.utc),
                        datetime.fromtimestamp(int(float(raw_kline[6])) / 1000, tz=timezone.utc),
                        raw_kline[1],
                        raw_kline[2],
                        raw_kline[3],
                        raw_kline[4],
                        raw_kline[5],
                        raw_kline[7],
                        raw_kline[8],
                        raw_kline[9],
                        raw_kline[10],
                    )
                    inserted_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"写入第 {i} 条K线失败: {symbol} {interval} open_time={raw_kline[0]}, error={e}")

        logger.debug(f"已写入 {inserted_count}/{len(raw_klines)} 条K线到 klines_history: {symbol} {interval} (errors={error_count})")
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
