"""
WS订阅管理器（统一版）

职责：
1. 【核心】监听数据库订阅通知 (subscription_add/remove/clean)
2. 【核心】统一调度所有WS客户端执行订阅/取消
3. 【核心】接收所有WS客户端的数据包
4. 【核心】统一将数据写入数据库
5. WS客户端生命周期管理（连接/断连/重连）

支持的数据类型：
- 市场数据：KLINE, QUOTES, TRADE - 通过公共WS流订阅
- 账户数据：USERDATA - 通过用户数据流订阅（推送账户更新和订单成交更新）

订阅键格式：
- 市场数据: BINANCE:{SYMBOL}[.后缀]@{DATA_TYPE}[_{RESOLUTION}]
  - 示例: BINANCE:BTCUSDT@KLINE_1, BINANCE:BTCUSDT.PERP@KLINE_60
- 账户数据: BINANCE:{ACCOUNT_TYPE}@USERDATA
  - 示例: BINANCE:SPOT@USERDATA, BINANCE:FUTURES@USERDATA
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from clients.base_ws_client import BaseWSClient, WSDataPackage
from constants.binance import BinanceAccountSubscriptionKey
from db.realtime_data_repository import RealtimeDataRepository
from models import WSSubscribeRequest, WSUnsubscribeRequest
from models.kline_models import (
    BinanceSpotKlineWSModel,
    BinanceFuturesKlineWSModel,
)
from models.ticker_models import (
    BinanceSpotTicker24hrWSModel,
    BinanceFuturesTicker24hrWSModel,
)
from models.ws_account_models import (
    BinanceSpotOutboundAccountPositionEvent,
    BinanceSpotBalanceUpdateEvent,
    BinanceSpotEventStreamTerminatedWSModel,
    BinanceFuturesAccountUpdateWSModel,
    BinanceFuturesTradeLiteWSModel,
    BinanceFuturesMarginCallWSModel,
    BinanceFuturesAlgoUpdateWSModel,
    BinanceFuturesStrategyUpdateWSModel,
    BinanceFuturesGridUpdateWSModel,
    BinanceFuturesConditionalOrderTriggerRejectWSModel,
    BinanceFuturesAccountConfigUpdateWSModel,
)
from models.order_models import (
    BinanceSpotExecutionReportEvent,
    BinanceFuturesOrderTradeUpdateWSModel,
)
from utils import interval_to_resolution

logger = logging.getLogger(__name__)


class WSSubscriptionManager:
    """WS订阅管理器（统一版）

    职责:
    1. 【核心】监听数据库订阅通知 (subscription_add/remove/clean)
    2. 【核心】统一调度所有WS客户端执行订阅/取消
    3. 【核心】接收所有WS客户端的数据包
    4. 【核心】统一将数据写入数据库
    5. WS客户端生命周期管理（连接/断连/重连）

    支持的数据类型：
    - 市场数据 (KLINE, QUOTES, TRADE): 通过公共WS流订阅
    - 账户数据 (ACCOUNT): 通过用户数据流订阅，无需符号订阅
    """

    # 用户数据流客户端 ID（与 BinanceService 中注册的 client_id 一致）
    SPOT_USER_STREAM_ID = "binance-spot-private-ws-001"
    FUTURES_USER_STREAM_ID = "binance-futures-private-ws-001"

    def __init__(self, pool: asyncpg.Pool) -> None:
        """初始化订阅管理器

        Args:
            pool: asyncpg 连接池
        """
        self._pool = pool
        self._repository = RealtimeDataRepository(pool)

        # WS客户端管理: client_id -> client
        self._ws_clients: dict[str, BaseWSClient] = {}

        # 账户订阅状态
        self._account_subscriptions: set[str] = set()  # 当前已订阅的账户键

        # 用户数据流客户端（账户订阅）- 不参与批量订阅
        self._user_stream_clients: dict[str, BaseWSClient] = {}

        # 批处理队列
        self._pending_subscribes: set[str] = set()
        self._pending_unsubscribes: set[str] = set()
        self._batch_lock = asyncio.Lock()

        # 批处理定时器
        self._running = False
        self._batch_task: Optional[asyncio.Task] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._BATCH_INTERVAL = 0.25  # 0.25秒批处理窗口

        # _full_sync_lock 保护 _full_sync_running 的原子检查与设置，
        # 实际同步操作在锁外执行，避免阻塞其他调用者
        self._full_sync_lock = asyncio.Lock()
        self._full_sync_running = False
        self._FULL_SYNC_MAX_RETRIES = 5
        self._FULL_SYNC_RETRY_DELAY = 2.0

    # ========== WS客户端注册 ==========

    def register_client(self, client_id: str, client: BaseWSClient) -> None:
        """注册市场数据WS客户端

        Args:
            client_id: 客户端唯一标识，如 "binance-spot-ws-001"
            client: WS客户端实例
        """
        self._ws_clients[client_id] = client
        # 设置数据回调，接收 WSDataPackage
        client.set_data_callback(self._handle_data_package)
        logger.info(f"已注册市场数据WS客户端: {client_id}")

    def register_user_stream_client(self, client_id: str, client: BaseWSClient) -> None:
        """注册用户数据流客户端（用于账户订阅）

        用户数据流客户端与市场数据客户端不同：
        - 不参与批量订阅/取消
        - 在 start() 时自动连接和订阅
        - 通过 client_id 区分数据类型

        Args:
            client_id: 客户端唯一标识，如 "binance-spot-user-stream-001"
            client: WS客户端实例
        """
        self._user_stream_clients[client_id] = client
        client.set_data_callback(self._handle_data_package)
        logger.info(f"已注册用户数据流客户端: {client_id}")

    # ========== 生命周期管理 ==========

    async def start(self) -> None:
        """启动管理器：连接所有WS客户端并开始监听

        启动时执行全量同步，恢复所有已存在的订阅。
        """
        if self._running:
            logger.warning("WSSubscriptionManager已在运行")
            return

        self._running = True

        # 启动批处理任务
        self._batch_task = asyncio.create_task(self._batch_loop())

        # 启动监听任务
        self._listener_task = asyncio.create_task(self._listen_notifications())

        # 启动市场数据WS客户端
        for client_id, client in self._ws_clients.items():
            try:
                await client.connect()
                logger.info(f"市场数据WS客户端已启动: {client_id}")
            except Exception as e:
                logger.error(f"市场数据WS客户端启动失败: {client_id}, {e}")

        # 启动用户数据流客户端（账户订阅）
        for client_id, client in self._user_stream_clients.items():
            try:
                await client.connect()
                logger.info(f"用户数据流客户端已启动: {client_id}")
            except Exception as e:
                logger.error(f"用户数据流客户端启动失败: {client_id}, {e}")

        # 启动时执行全量同步，恢复所有已存在的订阅
        await self.full_sync()

        logger.info("WSSubscriptionManager已启动")

    async def stop(self) -> None:
        """停止管理器：断开所有WS客户端连接"""
        if not self._running:
            return

        self._running = False

        # 取消批处理任务
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass

        # 取消监听任务
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        # 断开所有WS客户端
        for client_id, client in self._ws_clients.items():
            try:
                await client.disconnect()
                logger.info(f"市场数据WS客户端已停止: {client_id}")
            except Exception as e:
                logger.error(f"市场数据WS客户端停止失败: {client_id}, {e}")

        # 断开用户数据流客户端
        for client_id, client in self._user_stream_clients.items():
            try:
                await client.disconnect()
                logger.info(f"用户数据流客户端已停止: {client_id}")
            except Exception as e:
                logger.error(f"用户数据流客户端停止失败: {client_id}, {e}")

        logger.info("WSSubscriptionManager已停止")

    # ========== 数据包处理 ==========

    async def _handle_data_package(self, package: WSDataPackage) -> None:
        """处理WS数据包（统一入口）

        根据 client_id 路由到不同的处理函数：
        - 用户数据流客户端 -> 账户数据处理
        - 公共数据流客户端 -> 市场数据处理
        """
        logger.debug(f"[WS_DATA] 收到数据包: client={package.client_id}")

        # 判断是否为用户数据流客户端
        if package.client_id in (self.SPOT_USER_STREAM_ID, self.FUTURES_USER_STREAM_ID):
            await self._handle_account_data(package)
            return

        # 市场数据处理
        # binance-spot-ws-001 -> 现货，无后缀
        # binance-futures-ws-001 -> 期货，添加 .PERP 后缀
        is_futures = "futures" in package.client_id.lower()

        # 从数据中提取流名称并验证数据
        event_type = package.data.get("e", "")

        if event_type == "kline":
            await self._handle_kline_data(package.data, is_futures)
        elif event_type in ("24hrTicker", "BOOK_TICKER"):
            await self._handle_ticker_data(package.data, is_futures)
        else:
            # 其他类型，直接写入原始数据
            stream = self._extract_stream(package.data)
            if not stream:
                logger.warning(
                    f"[WS_DATA] 无法识别的数据格式: {event_type}"
                )
                return
            subscription_key = self._binance_stream_to_key(stream, is_futures)
            await self._write_realtime_data(subscription_key, package.data)

    async def _handle_kline_data(self, data: dict, is_futures: bool) -> None:
        """处理 K线数据

        使用 BinanceSpotKlineWSModel 或 BinanceFuturesKlineWSModel 验证数据，
        然后写入数据库。

        Args:
            data: 币安原始 WS 消息
            is_futures: 是否为期货数据
        """
        # 选择对应的模型
        kline_model_class = (
            BinanceFuturesKlineWSModel if is_futures else BinanceSpotKlineWSModel
        )

        try:
            # 使用 Pydantic 模型验证数据
            validated_model = kline_model_class.model_validate(data)

            # 提取流名称
            stream = self._extract_stream(data)
            if not stream:
                logger.warning("[WS_DATA] 无法从 kline 数据中提取流名称")
                return

            subscription_key = self._binance_stream_to_key(stream, is_futures)

            # 将验证后的数据写入数据库
            # 使用 model_dump(by_alias=True, mode='json') 获取验证后的字典数据：
            # - by_alias=True: 输出币安别名格式 (c, h, l, o 等)，而非 Pydantic 字段名 (close_price, high_price 等)
            # - mode='json': 自动处理 Decimal/ datetime 序列化为 JSON 兼容格式
            await self._write_realtime_data(
                subscription_key, validated_model.model_dump(by_alias=True, mode='json')
            )
            logger.debug(
                f"[WS_DATA] K线数据已验证并写入: {subscription_key}"
            )
        except Exception as e:
            logger.error(f"K线数据验证失败: {e}, data={data}")

    async def _handle_ticker_data(self, data: dict, is_futures: bool) -> None:
        """处理 Ticker 数据

        使用 BinanceSpotTicker24hrWSModel 或 BinanceFuturesTicker24hrWSModel 验证数据，
        然后写入数据库。

        Args:
            data: 币安原始 WS 消息
            is_futures: 是否为期货数据
        """
        # 选择对应的模型
        ticker_model_class = (
            BinanceFuturesTicker24hrWSModel
            if is_futures
            else BinanceSpotTicker24hrWSModel
        )

        try:
            # 使用 Pydantic 模型验证数据
            validated_model = ticker_model_class.model_validate(data)

            # 提取流名称
            stream = self._extract_stream(data)
            if not stream:
                logger.warning("[WS_DATA] 无法从 ticker 数据中提取流名称")
                return

            subscription_key = self._binance_stream_to_key(stream, is_futures)

            # 将验证后的数据写入数据库
            # 使用 model_dump(by_alias=True, mode='json') 获取验证后的字典数据：
            # - by_alias=True: 输出币安别名格式 (c, h, l, o 等)，而非 Pydantic 字段名 (close_price, high_price 等)
            # - mode='json': 自动处理 Decimal/ datetime 序列化为 JSON 兼容格式
            await self._write_realtime_data(
                subscription_key, validated_model.model_dump(by_alias=True, mode='json')
            )
            logger.debug(
                f"[WS_DATA] Ticker数据已验证并写入: {subscription_key}"
            )
        except Exception as e:
            logger.error(f"Ticker数据验证失败: {e}, data={data}")

    # ========== 账户数据处理 ==========

    async def _handle_account_data(self, package: WSDataPackage) -> None:
        """处理账户数据（用户数据流）

        消息格式：
        - 现货：{subscriptionId: 0, event: {e: "...", ...}}
        - 期货：{e: "ACCOUNT_UPDATE", E: ..., T: ..., a: {...}}

        重要：写入 realtime_data 表时，只取 event 字段内容（不包含 subscriptionId）
        以保持与期货数据格式一致。

        Args:
            package: WS数据包
        """
        is_spot = package.client_id == self.SPOT_USER_STREAM_ID
        subscription_key = (
            BinanceAccountSubscriptionKey.SPOT if is_spot
            else BinanceAccountSubscriptionKey.FUTURES
        )

        try:
            message = package.data
            # 现货数据：WS消息有 event 字段包装，如 {subscriptionId: 0, event: {...}}
            # 期货数据：WS消息直接是事件对象，如 {e: "ACCOUNT_UPDATE", E: ..., T: ..., a: {...}}
            # 因此期货数据直接使用 message 作为 event_data
            event_data = message.get("event", {}) if is_spot else message
            event_type = event_data.get("e", "unknown")

            logger.debug(f"[WS_ACCOUNT] 处理账户数据: {event_type}")

            # 现货账户数据：只取 event 字段进行验证和输出
            # 不包含 subscriptionId（它是 WS 协议的内部字段，无业务用途）
            if event_type == "outboundAccountPosition":
                # event_data 格式: {e: "outboundAccountPosition", E: ..., u: ..., B: [...]}
                ws_event = BinanceSpotOutboundAccountPositionEvent.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "balanceUpdate":
                # event_data 格式: {e: "balanceUpdate", E: ..., a: ..., d: ..., T: ...}
                ws_event = BinanceSpotBalanceUpdateEvent.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "executionReport":
                # event_data 格式: {e: "executionReport", E: ..., s: ..., ...}
                ws_event = BinanceSpotExecutionReportEvent.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "ACCOUNT_UPDATE":
                # 期货数据直接是事件对象
                ws_event = BinanceFuturesAccountUpdateWSModel.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "ORDER_TRADE_UPDATE":
                # 期货数据直接是事件对象
                ws_event = BinanceFuturesOrderTradeUpdateWSModel.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "TRADE_LITE":
                # 期货简化交易事件
                ws_event = BinanceFuturesTradeLiteWSModel.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "MARGIN_CALL":
                # 期货保证金追缴事件
                ws_event = BinanceFuturesMarginCallWSModel.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "ALGO_UPDATE":
                # 期货条件单更新事件
                ws_event = BinanceFuturesAlgoUpdateWSModel.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "STRATEGY_UPDATE":
                # 期货策略更新事件
                ws_event = BinanceFuturesStrategyUpdateWSModel.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "GRID_UPDATE":
                # 期货网格更新事件
                ws_event = BinanceFuturesGridUpdateWSModel.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "CONDITIONAL_ORDER_TRIGGER_REJECT":
                # 期货条件单触发拒绝事件
                ws_event = BinanceFuturesConditionalOrderTriggerRejectWSModel.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "ACCOUNT_CONFIG_UPDATE":
                # 期货账户配置更新事件
                ws_event = BinanceFuturesAccountConfigUpdateWSModel.model_validate(event_data)
                processed_data = ws_event.model_dump(by_alias=True, mode='json')
            elif event_type == "eventStreamTerminated":
                # 现货事件流终止事件 - 用户数据流已被正确关闭
                # 根据 Binance 官方文档，此事件在以下情况发送：
                # 1. listen token 订阅过期
                # 2. session.logout 后
                # 3. userDataStream.unsubscribe 停止订阅后
                # 这是控制事件，不写入数据库
                ws_event = BinanceSpotEventStreamTerminatedWSModel.model_validate(message)
                logger.info(
                    f"[WS_ACCOUNT] 现货用户数据流已终止: eventTime={ws_event.event.event_time}, "
                    f"subscriptionId={ws_event.subscription_id}"
                )
                return  # 不写入数据库，这是控制事件
            else:
                logger.warning(f"[WS_ACCOUNT] 未知事件类型: {event_type}，直接透传")
                processed_data = event_data

            await self._write_realtime_data(subscription_key, processed_data)
            logger.debug(f"[WS_ACCOUNT] 账户数据已更新: {event_type}")

        except Exception as e:
            logger.error(f"[WS_ACCOUNT] 处理账户数据失败: {e}")
            import traceback
            logger.error(f"[WS_ACCOUNT] 详细错误: {traceback.format_exc()}")

    async def _write_realtime_data(self, subscription_key: str, data: dict) -> None:
        """写入实时数据到数据库

        Args:
            subscription_key: 订阅键
            data: 已验证的数据字典
        """
        try:
            await self._repository.update_data(
                subscription_key=subscription_key,
                data=data,
                event_time=datetime.now(timezone.utc),
            )
            logger.debug(f"[WS_DATA] 写入数据: {subscription_key}")
        except Exception as e:
            logger.error(f"写入实时数据失败: {subscription_key}, {e}")

    def _extract_stream(self, data: dict) -> Optional[str]:
        """从币安数据中提取流名称

        Args:
            data: 币安原始WS消息

        Returns:
            流名称，如 "btcusdt@kline_1m" 或 None
        """
        event_type = data.get("e")

        if event_type == "kline":
            symbol = data.get("s", "").lower()
            interval = data.get("k", {}).get("i", "")
            return f"{symbol}@kline_{interval}"

        elif event_type == "24hrTicker":
            symbol = data.get("s", "").lower()
            return f"{symbol}@ticker"

        elif event_type == "trade":
            symbol = data.get("s", "").lower()
            return f"{symbol}@trade"

        return None

    def _binance_stream_to_key(self, stream: str, is_futures: bool = False) -> str:
        """币安流名称 -> 订阅键

        Args:
            stream: 币安流名称，如 "btcusdt@kline_1m" 或 "btcusdt@ticker"
            is_futures: 是否为期货数据（通过 client_id 判断）

        Returns:
            订阅键，如 "BINANCE:BTCUSDT@KLINE_1" 或 "BINANCE:BTCUSDT@QUOTES"

        说明：
        - 现货和期货K线都使用相同的 stream 格式
        - 通过 is_futures 参数添加正确的后缀
        - ticker -> QUOTES（TV格式映射）
        """
        # 解析 stream: btcusdt@kline_1m 或 btcusdt@ticker
        symbol_part, type_part = stream.split("@", 1)

        # 如果是期货数据，添加 .PERP 后缀
        if is_futures:
            symbol_part = f"{symbol_part}.PERP"

        # 提取数据类型和分辨率
        # kline_1m -> KLINE + 1m -> 1 (TV格式)
        # ticker -> QUOTES（TV格式映射）
        if "_" in type_part:
            data_type, interval = type_part.split("_", 1)
            data_type = data_type.upper()
            # 转换间隔格式: 1m -> 1, 1h -> 60, 1d -> D
            tv_resolution = interval_to_resolution(interval)
            return f"BINANCE:{symbol_part.upper()}@{data_type}_{tv_resolution}"

        # ticker -> QUOTES（TV格式映射）
        if type_part.upper() == "TICKER":
            return f"BINANCE:{symbol_part.upper()}@QUOTES"

        return f"BINANCE:{symbol_part.upper()}@{type_part.upper()}"

    # ========== 订阅通知处理 ==========

    async def _listen_notifications(self) -> None:
        """监听数据库订阅通知

        监听频道：subscription_add, subscription_remove, subscription_clean
        """
        conn: Optional[asyncpg.Connection] = None
        while self._running:
            try:
                conn = await self._pool.acquire()
                await conn.add_listener("subscription_add", self._notify_handler)
                await conn.add_listener("subscription_remove", self._notify_handler)
                await conn.add_listener("subscription_clean", self._notify_handler)

                logger.info("已注册订阅通知监听器")

                # 保持连接活跃
                while self._running:
                    await asyncio.sleep(5)
                    try:
                        await conn.fetchval("SELECT 1")
                    except Exception:
                        break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"订阅通知监听异常: {e}")
                await asyncio.sleep(5)
            finally:
                if conn:
                    await self._pool.release(conn)
                    conn = None

    def _notify_handler(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        """通知处理器"""
        logger.debug(
            f"[LISTEN] 收到通知: channel={channel}, pid={pid}, payload={payload[:100]}"
        )
        asyncio.create_task(self._handle_notification(channel, payload))

    async def _handle_notification(self, channel: str, payload: str) -> None:
        """处理通知

        注意：数据库通知采用统一包装格式：
        {
            "event_id": "...",
            "event_type": "subscription_add",
            "timestamp": "...",
            "data": {
                "subscription_key": "...",
                "data_type": "...",
                "created_at": "..."
            }
        }
        """
        logger.debug(f"[HANDLE] 处理通知: channel={channel}")
        try:
            data = json.loads(payload)

            if channel == "subscription_add":
                # 统一包装格式：数据在 data 字段中
                event_data = data.get("data", {})
                subscription_key = event_data.get("subscription_key")
                data_type = event_data.get("data_type")
                logger.debug(
                    f"[HANDLE] subscription_add: key={subscription_key}, type={data_type}"
                )
                if subscription_key and data_type:
                    await self._add_subscribe(subscription_key)

            elif channel == "subscription_remove":
                # 统一包装格式：数据在 data 字段中
                event_data = data.get("data", {})
                subscription_key = event_data.get("subscription_key")
                data_type = event_data.get("data_type")
                logger.debug(
                    f"[HANDLE] subscription_remove: key={subscription_key}, type={data_type}"
                )
                if subscription_key and data_type:
                    await self._add_unsubscribe(subscription_key)

            elif channel == "subscription_clean":
                await self._handle_clean_all()

        except json.JSONDecodeError:
            logger.error(f"无效的JSON载荷: {payload[:100]}")
        except Exception as e:
            logger.error(f"处理通知失败: {e}")

    # ========== 批处理 ==========

    async def _batch_loop(self) -> None:
        """批处理循环：每0.25秒执行待处理的订阅/取消"""
        while self._running:
            await asyncio.sleep(self._BATCH_INTERVAL)
            await self._flush_pending()

    async def _add_subscribe(self, subscription_key: str) -> None:
        """添加待订阅"""
        logger.debug(f"[BATCH] 添加待订阅: {subscription_key}")
        async with self._batch_lock:
            self._pending_subscribes.add(subscription_key)
            self._pending_unsubscribes.discard(subscription_key)
        logger.debug(f"[BATCH] 当前待订阅队列: {list(self._pending_subscribes)}")

    async def _add_unsubscribe(self, subscription_key: str) -> None:
        """添加待取消"""
        async with self._batch_lock:
            self._pending_unsubscribes.add(subscription_key)
            self._pending_subscribes.discard(subscription_key)

    async def _flush_pending(self) -> None:
        """执行待处理的订阅/取消"""
        async with self._batch_lock:
            subscribes = self._pending_subscribes.copy()
            unsubscribes = self._pending_unsubscribes.copy()
            self._pending_subscribes.clear()
            self._pending_unsubscribes.clear()

        if not subscribes and not unsubscribes:
            return

        logger.debug(
            f"[FLUSH] 执行批处理: subscribes={len(subscribes)}, unsubscribes={len(unsubscribes)}"
        )

        if subscribes:
            await self._execute_batch_subscribe(list(subscribes))

        if unsubscribes:
            await self._execute_batch_unsubscribe(list(unsubscribes))

    async def _execute_batch_subscribe(self, subscription_keys: list[str]) -> None:
        """执行批量订阅

        流程:
        1. 按 WS 客户端分组订阅键
        2. 检查客户端连接状态，未连接则重新入队等待下次批处理
        3. 每个客户端批量发送一个订阅请求

        账户订阅（BinanceAccountSubscriptionKey）使用用户数据流，无需符号订阅。
        """
        logger.info(f"[EXEC_SUB] 开始执行批量订阅: {len(subscription_keys)} 个订阅")

        # 按客户端分组: (key, stream) 保留 key 以便重入队
        spot_entries: list[tuple[str, str]] = []
        futures_entries: list[tuple[str, str]] = []
        account_subscriptions: list[str] = []

        for key in subscription_keys:
            if key in (BinanceAccountSubscriptionKey.SPOT, BinanceAccountSubscriptionKey.FUTURES):
                account_subscriptions.append(key)
                continue

            try:
                stream, is_futures = (
                    self._repository.subscription_key_to_binance_stream(key)
                )
                if is_futures:
                    futures_entries.append((key, stream))
                else:
                    spot_entries.append((key, stream))
            except Exception as e:
                logger.error(f"[EXEC_SUB] 解析订阅键失败: key={key}, error={e}")

        # 处理账户订阅
        if account_subscriptions:
            for sub_key in account_subscriptions:
                self._account_subscriptions.add(sub_key)
            logger.info(f"[EXEC_SUB] 账户订阅已激活: {account_subscriptions}")

            if BinanceAccountSubscriptionKey.SPOT in account_subscriptions:
                spot_user_client = self._user_stream_clients.get(self.SPOT_USER_STREAM_ID)
                if spot_user_client:
                    await spot_user_client.subscribe()
                    logger.info("[EXEC_SUB] 现货用户数据流已触发订阅")

            if BinanceAccountSubscriptionKey.FUTURES in account_subscriptions:
                futures_user_client = self._user_stream_clients.get(self.FUTURES_USER_STREAM_ID)
                if futures_user_client:
                    await futures_user_client.subscribe()
                    logger.info("[EXEC_SUB] 期货用户数据流已触发订阅")

        # 现货客户端批量订阅
        if spot_entries:
            client = self._ws_clients.get("binance-spot-ws-001")
            if client and client.is_connected:
                streams = [s for _, s in spot_entries]
                try:
                    request = WSSubscribeRequest(params=streams, id=id(self))
                    await client.subscribe(request)
                    logger.info(
                        f"[EXEC_SUB] 现货批量订阅成功: {len(streams)} 个流"
                    )
                except Exception as e:
                    logger.error(f"[EXEC_SUB] 现货批量订阅失败: {e}")
            elif client:
                logger.warning(
                    f"[EXEC_SUB] 现货客户端未连接，{len(spot_entries)} 个订阅将在重连后由 full_sync 恢复"
                )
            else:
                logger.error("[EXEC_SUB] 现货客户端不存在")

        # 期货客户端批量订阅
        if futures_entries:
            client = self._ws_clients.get("binance-futures-ws-001")
            if client and client.is_connected:
                streams = [s for _, s in futures_entries]
                try:
                    request = WSSubscribeRequest(params=streams, id=id(self))
                    await client.subscribe(request)
                    logger.info(
                        f"[EXEC_SUB] 期货批量订阅成功: {len(streams)} 个流"
                    )
                except Exception as e:
                    logger.error(f"[EXEC_SUB] 期货批量订阅失败: {e}")
            elif client:
                logger.warning(
                    f"[EXEC_SUB] 期货客户端未连接，{len(futures_entries)} 个订阅将在重连后由 full_sync 恢复"
                )
            else:
                logger.error("[EXEC_SUB] 期货客户端不存在")

    async def _execute_batch_unsubscribe(self, subscription_keys: list[str]) -> None:
        """执行批量取消订阅"""
        logger.info(
            f"[EXEC_UNSUB] 开始执行批量取消订阅: {len(subscription_keys)} 个订阅"
        )

        spot_entries: list[tuple[str, str]] = []
        futures_entries: list[tuple[str, str]] = []
        account_subscriptions: list[str] = []

        for key in subscription_keys:
            if key in (BinanceAccountSubscriptionKey.SPOT, BinanceAccountSubscriptionKey.FUTURES):
                account_subscriptions.append(key)
                continue

            try:
                stream, is_futures = (
                    self._repository.subscription_key_to_binance_stream(key)
                )
                if is_futures:
                    futures_entries.append((key, stream))
                else:
                    spot_entries.append((key, stream))
            except Exception as e:
                logger.error(f"[EXEC_UNSUB] 解析订阅键失败: key={key}, error={e}")

        # 处理账户取消订阅
        if account_subscriptions:
            for sub_key in account_subscriptions:
                self._account_subscriptions.discard(sub_key)
            logger.info(f"[EXEC_UNSUB] 账户订阅已移除: {account_subscriptions}")

            if BinanceAccountSubscriptionKey.SPOT in account_subscriptions:
                spot_user_client = self._user_stream_clients.get(self.SPOT_USER_STREAM_ID)
                if spot_user_client:
                    await spot_user_client.unsubscribe()
                    logger.info("[EXEC_UNSUB] 现货用户数据流已取消订阅")

            if BinanceAccountSubscriptionKey.FUTURES in account_subscriptions:
                futures_user_client = self._user_stream_clients.get(self.FUTURES_USER_STREAM_ID)
                if futures_user_client:
                    await futures_user_client.unsubscribe()
                    logger.info("[EXEC_UNSUB] 期货用户数据流已取消订阅")

        # 现货客户端批量取消订阅（仅已连接时发送）
        if spot_entries:
            client = self._ws_clients.get("binance-spot-ws-001")
            if client and client.is_connected:
                streams = [s for _, s in spot_entries]
                try:
                    request = WSUnsubscribeRequest(params=streams, id=id(self))
                    await client.unsubscribe(request)
                    logger.info(
                        f"[EXEC_UNSUB] 现货批量取消订阅成功: {len(streams)} 个流"
                    )
                except Exception as e:
                    logger.error(f"[EXEC_UNSUB] 现货批量取消订阅失败: {e}")
            elif client:
                logger.warning(
                    f"[EXEC_UNSUB] 现货客户端未连接，{len(spot_entries)} 个取消订阅将在重连后由 full_sync 处理"
                )

        # 期货客户端批量取消订阅（仅已连接时发送）
        if futures_entries:
            client = self._ws_clients.get("binance-futures-ws-001")
            if client and client.is_connected:
                streams = [s for _, s in futures_entries]
                try:
                    request = WSUnsubscribeRequest(params=streams, id=id(self))
                    await client.unsubscribe(request)
                    logger.info(
                        f"[EXEC_UNSUB] 期货批量取消订阅成功: {len(streams)} 个流"
                    )
                except Exception as e:
                    logger.error(f"[EXEC_UNSUB] 期货批量取消订阅失败: {e}")
            elif client:
                logger.warning(
                    f"[EXEC_UNSUB] 期货客户端未连接，{len(futures_entries)} 个取消订阅将在重连后由 full_sync 处理"
                )

    async def _handle_clean_all(self) -> None:
        """处理 clean_all 通知：执行全量同步恢复订阅。

        clean_all 表示 realtime_data 表已被清空并重建（如 subscription-manager
        重启时的状态核对）。直接调用 full_sync() 从数据库读取当前订阅并重新执行，
        不调用 disconnect()，因为那会设置 _running=False 永久阻塞客户端恢复。
        """
        logger.info("收到 clean_all 通知，执行全量同步恢复订阅")
        await self.full_sync()

    async def full_sync(self) -> None:
        """全量同步：从数据库读取所有订阅并执行订阅

        用于断线重连后恢复订阅。
        包括市场数据订阅和账户订阅（用户数据流）。

        使用 _full_sync_lock 防止多个 WS 客户端同时重连导致并发执行。
        """
        # 原子检查并设置运行标志，避免 TOCTOU 竞态
        async with self._full_sync_lock:
            if self._full_sync_running:
                logger.info("全量同步已在执行中，跳过重复调用")
                return
            self._full_sync_running = True

        try:
            for attempt in range(1, self._FULL_SYNC_MAX_RETRIES + 1):
                try:
                    logger.info(
                        "执行全量同步... (第 %d/%d 次)",
                        attempt, self._FULL_SYNC_MAX_RETRIES,
                    )
                    async with self._pool.acquire() as conn:
                        rows = await conn.fetch(
                            "SELECT subscription_key, data_type FROM realtime_data"
                        )

                    if rows:
                        market_subscription_keys = [
                            row["subscription_key"] for row in rows
                            if row["subscription_key"] not in (
                                BinanceAccountSubscriptionKey.SPOT,
                                BinanceAccountSubscriptionKey.FUTURES,
                            )
                        ]
                        data_types = [
                            row["data_type"] for row in rows
                            if row["subscription_key"] not in (
                                BinanceAccountSubscriptionKey.SPOT,
                                BinanceAccountSubscriptionKey.FUTURES,
                            )
                        ]

                        spot_user_client = self._user_stream_clients.get(self.SPOT_USER_STREAM_ID)
                        futures_user_client = self._user_stream_clients.get(self.FUTURES_USER_STREAM_ID)

                        for row in rows:
                            if row["subscription_key"] == BinanceAccountSubscriptionKey.SPOT:
                                self._account_subscriptions.add(row["subscription_key"])
                                if spot_user_client:
                                    await spot_user_client.subscribe()
                                    logger.info("[FULL_SYNC] 现货用户数据流已触发动态订阅")
                            elif row["subscription_key"] == BinanceAccountSubscriptionKey.FUTURES:
                                self._account_subscriptions.add(row["subscription_key"])
                                if futures_user_client:
                                    await futures_user_client.subscribe()
                                    logger.info("[FULL_SYNC] 期货用户数据流已触发动态订阅")

                        logger.info(
                            f"全量同步：发现 {len(market_subscription_keys)} 个市场订阅: {data_types}"
                        )
                        if self._account_subscriptions:
                            logger.info(
                                f"全量同步：账户订阅已激活: {list(self._account_subscriptions)}"
                            )

                        await self._execute_batch_subscribe(market_subscription_keys)
                    else:
                        logger.info("全量同步：无订阅")

                    return  # 成功

                except Exception as e:
                    logger.error(
                        "全量同步失败 (第 %d/%d 次): %s",
                        attempt, self._FULL_SYNC_MAX_RETRIES, e,
                    )
                    if attempt < self._FULL_SYNC_MAX_RETRIES:
                        await asyncio.sleep(self._FULL_SYNC_RETRY_DELAY)

            logger.error(
                "全量同步 %d 次重试全部失败，放弃，等待下次重连触发",
                self._FULL_SYNC_MAX_RETRIES,
            )
        finally:
            self._full_sync_running = False
