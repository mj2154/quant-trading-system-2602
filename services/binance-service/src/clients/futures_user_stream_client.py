"""
期货用户数据流客户端

专门接收期货账户更新数据的 WebSocket 客户端。

职责：
1. 根据给定的 listenKey 连接到 wss://fstream.binancefuture.com/ws/<listenKey>
2. 接收账户更新事件（ACCOUNT_UPDATE, ORDER_TRADE_UPDATE, listenKeyExpired）
3. 将数据打包为 WSDataPackage 传递给 BinanceService

设计原则：
- 不保存 listenKey，只使用传入的参数
- 不自动重连，断开时通过回调通知 BinanceService
- 所有 listenKey 管理（创建/续期/停止）由 BinanceService 通过 FuturesPrivateWSClient 执行

端点（Testnet）:
- WebSocket: wss://fstream.binancefuture.com

文档: binance_futures_docs/01_USDⓈ-M Futures/02_User Data Streams/
"""

import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from clients.base_ws_client import WSDataPackage

logger = logging.getLogger(__name__)


class FuturesUserDataStreamClient:
    """期货用户数据流客户端（专用数据流接收）

    职责：
    - 根据 listenKey 建立 WebSocket 连接
    - 接收账户更新事件并传递给 BinanceService
    - 断开时通知 BinanceService（不自动重连）

    注意：
    - 不保存 listenKey，每次 start() 时传入
    - 不管理 listenKey 的生命周期（创建/续期/停止）由 FuturesPrivateWSClient 负责
    - 连接断开时只通知 BinanceService，由其决定是否重连及使用哪个 key

    端点（Testnet）:
    - WebSocket: wss://fstream.binancefuture.com/ws/<listenKey>
    """

    CLIENT_ID = "binance-futures-user-stream-001"
    WS_URI = "wss://fstream.binancefuture.com/ws"

    # 重连间隔（秒）
    RECONNECT_DELAY = 2

    def __init__(
        self,
        api_key: str,
        private_key_pem: bytes,
        proxy_url: Optional[str] = None,
    ) -> None:
        """初始化客户端

        Args:
            api_key: 币安 API Key（仅用于标识）
            private_key_pem: 私钥 PEM 格式（未使用，保留兼容性）
            proxy_url: 可选的代理 URL
        """
        self._api_key = api_key
        self._proxy_url = proxy_url

        # 连接状态
        self._running = False
        self._connected = False

        # WebSocket
        self._websocket = None
        self._receive_task: Optional[asyncio.Task] = None

        # 回调
        self._data_callback: Optional[Callable[[WSDataPackage], Awaitable[None]]] = None
        # 断开时通知 BinanceService，由其决定是否重连
        self._reconnect_callback: Optional[Callable[[], Awaitable[None]]] = None

    @property
    def client_id(self) -> str:
        return self.CLIENT_ID

    @property
    def is_connected(self) -> bool:
        return self._connected

    def set_data_callback(self, callback: Callable[[WSDataPackage], Awaitable[None]]) -> None:
        """设置数据回调（BinanceService 接收数据用）"""
        self._data_callback = callback

    def set_reconnect_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """设置断连重连回调

        连接断开时调用，通知 BinanceService 由其决定如何处理重连。
        BinanceService 会检查 listenKey 是否有效，然后调用 start(newKey) 或 start(savedKey)。
        """
        self._reconnect_callback = callback

    async def start(self, listen_key: str) -> bool:
        """启动客户端

        使用指定的 listenKey 连接到 WebSocket 数据流。

        Args:
            listen_key: listenKey（由 BinanceService 传入）

        Returns:
            是否成功启动
        """
        if self._running and self._connected:
            logger.warning(f"[{self.CLIENT_ID}] 已在运行，先停止再启动")
            await self.stop()

        self._running = True

        try:
            # 建立 WebSocket 连接
            ws_url = f"{self.WS_URI}/{listen_key}"
            connect_kwargs: dict[str, Any] = {}
            if self._proxy_url:
                connect_kwargs["proxy"] = self._proxy_url

            self._websocket = await connect(ws_url, **connect_kwargs)
            self._connected = True
            logger.info(f"[{self.CLIENT_ID}] WebSocket 已连接")

            # 启动接收循环
            self._receive_task = asyncio.create_task(self._receive_loop())

            return True

        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 启动失败: {e}")
            self._connected = False
            self._running = False
            return False

    async def stop(self) -> None:
        """停止客户端

        断开 WebSocket 连接，不调用任何 stop API。
        listenKey 的关闭由 BinanceService 通过 FuturesPrivateWSClient.stop_listen_key() 执行。
        """
        if not self._running:
            return

        logger.info(f"[{self.CLIENT_ID}] 正在停止...")

        self._running = False
        self._connected = False

        # 取消接收任务
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # 关闭 WebSocket
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.warning(f"[{self.CLIENT_ID}] 关闭 WebSocket 出错: {e}")
            self._websocket = None

        logger.info(f"[{self.CLIENT_ID}] 已停止")

    async def _receive_loop(self) -> None:
        """接收数据循环"""
        logger.info(f"[{self.CLIENT_ID}] 接收循环启动")

        try:
            async for message in self._websocket:
                if not self._running:
                    break

                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"[{self.CLIENT_ID}] 无效 JSON 消息")
                except Exception as e:
                    logger.error(f"[{self.CLIENT_ID}] 处理消息出错: {e}")

        except asyncio.CancelledError:
            logger.info(f"[{self.CLIENT_ID}] 接收循环已取消")
        except ConnectionClosed:
            logger.warning(f"[{self.CLIENT_ID}] 连接已关闭")
        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 接收循环异常: {e}")
        finally:
            self._connected = False

            if self._running and self._reconnect_callback:
                # 通知 BinanceService，由其决定如何处理重连
                logger.info(f"[{self.CLIENT_ID}] 通知上层处理断连...")
                try:
                    await self._reconnect_callback()
                except Exception as e:
                    logger.error(f"[{self.CLIENT_ID}] 调用重连回调失败: {e}")

                # 等待上层调用 start() 重连
                # 如果上层没有立即调用 start()，这里会继续等待
                while self._running and not self._connected:
                    await asyncio.sleep(self.RECONNECT_DELAY)

    async def _handle_message(self, message: dict) -> None:
        """处理接收到的消息

        将数据打包为 WSDataPackage 传递给 BinanceService。
        """
        event_type = message.get("e", "unknown")
        logger.debug(f"[{self.CLIENT_ID}] 收到事件: {event_type}")

        package = WSDataPackage(
            client_id=self.CLIENT_ID,
            data=message,
            timestamp=int(time.time() * 1000),
        )

        if self._data_callback:
            try:
                await self._data_callback(package)
            except Exception as e:
                logger.error(f"[{self.CLIENT_ID}] 数据回调失败: {e}")
