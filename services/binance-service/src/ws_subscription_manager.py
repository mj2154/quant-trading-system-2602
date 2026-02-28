"""
WS订阅管理器

职责：
1. 【核心】监听数据库订阅通知 (subscription.add/remove/clean)
2. 【核心】统一调度所有WS客户端执行订阅/取消
3. 【核心】接收所有WS客户端的数据包
4. 【核心】统一将数据写入数据库
5. WS客户端生命周期管理（连接/断连/重连）

订阅键格式 (QUANT_TRADING_SYSTEM_ARCHITECTURE.md):
- {EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{RESOLUTION}]
- 示例: BINANCE:BTCUSDT@KLINE_1, BINANCE:BTCUSDT.PERP@KLINE_60

分辨率格式 (TradingView API规范):
- TV格式: "1", "60", "D", "W", "M"
- 币安格式: "1m", "1h", "1d", "1w", "1M"
- 系统内部统一使用TV格式

数据流:
1. 监听数据库 subscription.add/remove/clean 通知
2. 批处理后执行 WS 订阅/取消
3. 接收 WS 数据包，解析并写入 realtime_data 表
4. 触发 realtime_update 通知
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from clients.base_ws_client import BaseWSClient, WSDataPackage
from db.realtime_data_repository import RealtimeDataRepository
from utils import interval_to_resolution

logger = logging.getLogger(__name__)


class WSSubscriptionManager:
    """WS订阅管理器（币安服务专用）- 订阅管理核心

    职责:
    1. 【核心】监听数据库订阅通知 (subscription.add/remove/clean)
    2. 【核心】统一调度所有WS客户端执行订阅/取消
    3. 【核心】接收所有WS客户端的数据包
    4. 【核心】统一将数据写入数据库
    5. WS客户端生命周期管理（连接/断连/重连）
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """初始化订阅管理器

        Args:
            pool: asyncpg 连接池
        """
        self._pool = pool
        self._repository = RealtimeDataRepository(pool)

        # WS客户端管理: client_id -> client
        self._ws_clients: dict[str, BaseWSClient] = {}

        # 批处理队列
        self._pending_subscribes: set[str] = set()
        self._pending_unsubscribes: set[str] = set()
        self._batch_lock = asyncio.Lock()

        # 批处理定时器
        self._running = False
        self._batch_task: Optional[asyncio.Task] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._BATCH_INTERVAL = 0.25  # 0.25秒批处理窗口

    # ========== WS客户端注册 ==========

    def register_client(self, client_id: str, client: BaseWSClient) -> None:
        """注册WS客户端

        Args:
            client_id: 客户端唯一标识，如 "binance-spot-ws-001"
            client: WS客户端实例
        """
        self._ws_clients[client_id] = client
        # 设置数据回调，接收 WSDataPackage
        client.set_data_callback(self._handle_data_package)
        logger.info(f"已注册WS客户端: {client_id}")

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

        # 启动所有WS客户端连接
        for client_id, client in self._ws_clients.items():
            try:
                await client.connect()
                logger.info(f"WS客户端已启动: {client_id}")
            except Exception as e:
                logger.error(f"WS客户端启动失败: {client_id}, {e}")

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
                logger.info(f"WS客户端已停止: {client_id}")
            except Exception as e:
                logger.error(f"WS客户端停止失败: {client_id}, {e}")

        logger.info("WSSubscriptionManager已停止")

    # ========== 数据包处理 ==========

    async def _handle_data_package(self, package: WSDataPackage) -> None:
        """处理WS数据包（统一入口）

        解析数据包，统一写入数据库

        币安WS消息格式:
        {
            "e": "kline",           // 事件类型
            "s": "BTCUSDT",          // 交易对
            "k": {
                "i": "1m",           // K线间隔
                "o": "50000.00",    // 开盘价
                ...
            }
        }

        说明：
        - 现货和期货K线都使用相同的 stream 格式：btcusdt@kline_1m
        - 通过 package.client_id 区分数据来源，添加正确的后缀
        """
        logger.debug(f"[WS_DATA] 收到数据包: client={package.client_id}")

        # 从数据中提取流名称
        stream = self._extract_stream(package.data)
        if not stream:
            logger.warning(
                f"[WS_DATA] 无法识别的数据格式: {package.data.get('e', 'unknown')}"
            )
            return

        # 通过 client_id 判断数据来源，添加正确的后缀
        # binance-spot-ws-001 -> 现货，无后缀
        # binance-futures-ws-001 -> 期货，添加 .PERP 后缀
        is_futures = "futures" in package.client_id.lower()
        subscription_key = self._binance_stream_to_key(stream, is_futures)

        try:
            # 写入 realtime_data 表
            await self._repository.update_data(
                subscription_key=subscription_key,
                data=package.data,
                event_time=datetime.now(timezone.utc),
            )
            logger.debug(
                f"[WS_DATA] 写入数据: {subscription_key} from {package.client_id}"
            )
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

        监听频道：subscription.add, subscription.remove, subscription.clean
        """
        conn: Optional[asyncpg.Connection] = None
        while self._running:
            try:
                conn = await self._pool.acquire()
                await conn.add_listener("subscription.add", self._notify_handler)
                await conn.add_listener("subscription.remove", self._notify_handler)
                await conn.add_listener("subscription.clean", self._notify_handler)

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
            "event_type": "subscription.add",
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

            if channel == "subscription.add":
                # 统一包装格式：数据在 data 字段中
                event_data = data.get("data", {})
                subscription_key = event_data.get("subscription_key")
                data_type = event_data.get("data_type")
                logger.debug(
                    f"[HANDLE] subscription.add: key={subscription_key}, type={data_type}"
                )
                if subscription_key and data_type:
                    await self._add_subscribe(subscription_key)

            elif channel == "subscription.remove":
                # 统一包装格式：数据在 data 字段中
                event_data = data.get("data", {})
                subscription_key = event_data.get("subscription_key")
                data_type = event_data.get("data_type")
                logger.debug(
                    f"[HANDLE] subscription.remove: key={subscription_key}, type={data_type}"
                )
                if subscription_key and data_type:
                    await self._add_unsubscribe(subscription_key)

            elif channel == "subscription.clean":
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
        2. 每个客户端批量发送一个订阅请求
        """
        logger.info(f"[EXEC_SUB] 开始执行批量订阅: {len(subscription_keys)} 个订阅")

        # 按客户端分组订阅键
        spot_streams: list[str] = []
        futures_streams: list[str] = []

        for key in subscription_keys:
            try:
                stream, is_futures = (
                    self._repository.subscription_key_to_binance_stream(key)
                )
                if is_futures:
                    futures_streams.append(stream)
                else:
                    spot_streams.append(stream)
            except Exception as e:
                logger.error(f"[EXEC_SUB] 解析订阅键失败: key={key}, error={e}")

        # 现货客户端批量订阅
        if spot_streams:
            client = self._ws_clients.get("binance-spot-ws-001")
            if client:
                try:
                    await client.subscribe(spot_streams)
                    logger.info(
                        f"[EXEC_SUB] 现货批量订阅成功: {len(spot_streams)} 个流"
                    )
                except Exception as e:
                    logger.error(f"[EXEC_SUB] 现货批量订阅失败: {e}")
            else:
                logger.error("[EXEC_SUB] 现货客户端不存在")

        # 期货客户端批量订阅
        if futures_streams:
            client = self._ws_clients.get("binance-futures-ws-001")
            if client:
                try:
                    await client.subscribe(futures_streams)
                    logger.info(
                        f"[EXEC_SUB] 期货批量订阅成功: {len(futures_streams)} 个流"
                    )
                except Exception as e:
                    logger.error(f"[EXEC_SUB] 期货批量订阅失败: {e}")
            else:
                logger.error("[EXEC_SUB] 期货客户端不存在")

    async def _execute_batch_unsubscribe(self, subscription_keys: list[str]) -> None:
        """执行批量取消订阅"""
        logger.info(
            f"[EXEC_UNSUB] 开始执行批量取消订阅: {len(subscription_keys)} 个订阅"
        )

        # 按客户端分组订阅键
        spot_streams: list[str] = []
        futures_streams: list[str] = []

        for key in subscription_keys:
            try:
                stream, is_futures = (
                    self._repository.subscription_key_to_binance_stream(key)
                )
                if is_futures:
                    futures_streams.append(stream)
                else:
                    spot_streams.append(stream)
            except Exception as e:
                logger.error(f"[EXEC_UNSUB] 解析订阅键失败: key={key}, error={e}")

        # 现货客户端批量取消订阅
        if spot_streams:
            client = self._ws_clients.get("binance-spot-ws-001")
            if client:
                try:
                    await client.unsubscribe(spot_streams)
                    logger.info(
                        f"[EXEC_UNSUB] 现货批量取消订阅成功: {len(spot_streams)} 个流"
                    )
                except Exception as e:
                    logger.error(f"[EXEC_UNSUB] 现货批量取消订阅失败: {e}")

        # 期货客户端批量取消订阅
        if futures_streams:
            client = self._ws_clients.get("binance-futures-ws-001")
            if client:
                try:
                    await client.unsubscribe(futures_streams)
                    logger.info(
                        f"[EXEC_UNSUB] 期货批量取消订阅成功: {len(futures_streams)} 个流"
                    )
                except Exception as e:
                    logger.error(f"[EXEC_UNSUB] 期货批量取消订阅失败: {e}")

    async def _handle_clean_all(self) -> None:
        """处理 clean_all 通知：触发WS客户端重连并恢复订阅"""
        logger.info("收到 clean_all 通知，WS客户端将重连")
        for client in self._ws_clients.values():
            await client.disconnect()
        # 重连后恢复所有订阅
        await self.full_sync()

    async def full_sync(self) -> None:
        """全量同步：从数据库读取所有订阅并执行订阅

        用于断线重连后恢复订阅。
        """
        logger.info("执行全量同步...")
        try:
            async with self._pool.acquire() as conn:
                # 查询所有类型的订阅
                rows = await conn.fetch(
                    "SELECT subscription_key, data_type FROM realtime_data"
                )

            if rows:
                subscription_keys = [row["subscription_key"] for row in rows]
                data_types = [row["data_type"] for row in rows]
                logger.info(
                    f"全量同步：发现 {len(subscription_keys)} 个订阅: {data_types}"
                )
                await self._execute_batch_subscribe(subscription_keys)
            else:
                logger.info("全量同步：无订阅")

        except Exception as e:
            logger.error(f"全量同步失败: {e}")
