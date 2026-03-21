"""
期货用户数据流客户端

管理期货账户的 listenKey 创建、续期和 WebSocket 连接。
接收期货账户更新事件（ACCOUNT_UPDATE, ORDER_TRADE_UPDATE）。

设计原则（与 SpotUserStreamClient 一致）：
- WS客户端只负责连接和接收数据
- 收到数据后立即打包为 WSDataPackage，发送给币安服务
- 不维护任何回调或订阅状态
- 所有数据处理由币安服务统一完成

端点（Testnet）:
- REST API: https://demo-fapi.binance.com
- WebSocket: wss://fstream.binancefuture.com

文档: binance_futures_docs/01_U本位合约/02_Websocket账户信息推送/
"""

import asyncio
import json
import logging
import time
from typing import Any, Optional

import httpx
from websockets.asyncio.client import connect

from clients.base_ws_client import WSDataPackage

logger = logging.getLogger(__name__)


class FuturesUserStreamClient:
    """期货用户数据流客户端

    继承 BaseWSClient 统一客户端模式：
    - connect() -> 建立连接
    - disconnect() -> 断开连接
    - 接收数据 -> 打包为 WSDataPackage -> 调用 _data_callback

    职责：
    1. 管理 listenKey 的创建、续期和关闭
    2. 建立 WebSocket 连接接收账户更新事件
    3. 将接收到的原始数据打包为 WSDataPackage 传递给调用方

    数据流程：
    1. start() -> 创建 listenKey -> 建立 WebSocket 连接
    2. 接收事件 -> 打包为 WSDataPackage -> 调用 _data_callback
    3. stop() -> 关闭 WebSocket -> 关闭 listenKey

    事件类型：
    - ACCOUNT_UPDATE: 账户余额和持仓变化
    - ORDER_TRADE_UPDATE: 订单和成交更新

    端点（Testnet）:
    - REST API: https://demo-fapi.binance.com
    - WebSocket: wss://fstream.binancefuture.com
    """

    # listenKey 有效期（毫秒）
    LISTEN_KEY_EXPIRY_MS = 60 * 60 * 1000  # 60分钟
    # 续期间隔（秒），提前5分钟续期
    RENEW_INTERVAL_SEC = (LISTEN_KEY_EXPIRY_MS / 1000) - 5 * 60

    # 客户端标识
    CLIENT_ID = "binance-futures-user-stream-001"
    # Testnet WebSocket 端点
    WS_URI = "wss://fstream.binancefuture.com/ws"

    def __init__(
        self,
        api_key: str,
        private_key_pem: bytes,
        signature_type: str = "ed25519",
        proxy_url: Optional[str] = None,
    ) -> None:
        """初始化客户端

        Args:
            api_key: 币安 API Key
            private_key_pem: 私钥 PEM 格式
            signature_type: 签名类型 ("ed25519" 或 "rsa")
            proxy_url: 可选的代理 URL
        """
        self._api_key = api_key
        self._private_key_pem = private_key_pem
        self._signature_type = signature_type
        self._proxy_url = proxy_url

        self._listen_key: Optional[str] = None
        self._ws_connection: Optional[Any] = None
        self._running = False
        self._connected = False
        self._receive_task: Optional[asyncio.Task] = None
        self._renew_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._data_callback: Optional[Any] = None
        self._reconnect_callback: Optional[Any] = None

    @property
    def client_id(self) -> str:
        """客户端标识"""
        return self.CLIENT_ID

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    def set_data_callback(self, callback: Any) -> None:
        """设置数据回调（币安服务接收数据用）

        Args:
            callback: 异步回调函数，接收 WSDataPackage
        """
        self._data_callback = callback

    def set_reconnect_callback(self, callback: Any) -> None:
        """设置断线重连回调

        Args:
            callback: 断线重连时的回调函数
        """
        self._reconnect_callback = callback

    async def start(self) -> bool:
        """启动客户端

        Returns:
            是否成功启动
        """
        if self._running:
            logger.warning("期货用户数据流客户端已在运行")
            return True

        try:
            # 1. 创建 listenKey
            self._listen_key = await self._create_listen_key()
            if not self._listen_key:
                logger.error("创建期货 listenKey 失败")
                return False

            logger.info(f"期货 listenKey 已创建: {self._listen_key[:10]}...")

            # 2. 建立 WebSocket 连接（Testnet）
            ws_url = f"{self.WS_URI}/{self._listen_key}"
            connect_kwargs: dict[str, Any] = {}
            if self._proxy_url:
                connect_kwargs["proxy"] = self._proxy_url

            self._ws_connection = await connect(ws_url, **connect_kwargs)
            self._running = True
            self._connected = True

            logger.info("期货用户数据流 WebSocket 已连接 (Testnet)")

            # 3. 启动接收循环
            self._receive_task = asyncio.create_task(self._receive_loop())

            # 4. 启动续期任务
            self._renew_task = asyncio.create_task(self._renew_loop())

            return True

        except Exception as e:
            logger.error(f"启动期货用户数据流客户端失败: {e}")
            self._connected = False
            await self.stop()
            return False

    async def stop(self) -> None:
        """停止客户端"""
        if not self._running:
            return

        logger.info("停止期货用户数据流客户端...")
        self._running = False
        self._connected = False

        # 取消续期任务
        if self._renew_task:
            self._renew_task.cancel()
            try:
                await self._renew_task
            except asyncio.CancelledError:
                pass
            self._renew_task = None

        # 取消接收任务
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # 取消重连任务
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None

        # 关闭 WebSocket
        if self._ws_connection:
            try:
                await self._ws_connection.close()
            except Exception as e:
                logger.warning(f"关闭 WebSocket 时出错: {e}")
            self._ws_connection = None

        # 关闭 listenKey
        if self._listen_key:
            await self._close_listen_key(self._listen_key)
            self._listen_key = None

        logger.info("期货用户数据流客户端已停止")

    async def _receive_loop(self) -> None:
        """接收数据循环"""
        logger.info("期货用户数据流接收循环启动")

        try:
            async for message in self._ws_connection:
                if not self._running:
                    break

                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning("收到无效的 JSON 消息")
                except Exception as e:
                    logger.error(f"处理期货用户数据流消息时出错: {e}")

        except asyncio.CancelledError:
            logger.info("期货用户数据流接收循环已取消")
        except Exception as e:
            logger.error(f"期货用户数据流接收循环异常: {e}")
        finally:
            self._connected = False
            if self._running:
                # 尝试重新连接
                logger.info("期货用户数据流断开，尝试重新连接...")
                await self._reconnect()

    async def _handle_message(self, message: dict) -> None:
        """处理接收到的消息

        BaseWSClient 模式：
        - 收到数据后立即打包为 WSDataPackage
        - 调用 _data_callback 发送给币安服务
        - 不做任何数据解析
        """
        event_type = message.get("e", "unknown")
        logger.debug(f"[{self.CLIENT_ID}] 收到期货账户事件: {event_type}")

        # 打包数据并发送给币安服务（不解析）
        package = WSDataPackage(
            client_id=self.CLIENT_ID,
            data=message,  # 发送原始消息，不解析
            timestamp=int(time.time() * 1000),
        )

        if self._data_callback:
            try:
                await self._data_callback(package)
            except Exception as e:
                logger.error(f"调用数据回调失败: {e}")

    async def _renew_loop(self) -> None:
        """续期循环

        每隔 RENEW_INTERVAL_SEC 秒续期一次 listenKey
        """
        logger.info("期货用户数据流续期循环启动")

        while self._running:
            try:
                await asyncio.sleep(self.RENEW_INTERVAL_SEC)
                if not self._running:
                    break

                # 续期 listenKey
                success = await self._renew_listen_key()
                if success:
                    logger.debug("期货 listenKey 续期成功")
                else:
                    logger.warning("期货 listenKey 续期失败")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"期货 listenKey 续期循环异常: {e}")

        logger.info("期货用户数据流续期循环结束")

    async def _reconnect(self) -> None:
        """断线重连

        重连后需要重新：
        1. 创建新的 listenKey
        2. 建立 WebSocket 连接
        """
        if not self._running:
            return

        logger.info(f"[{self.CLIENT_ID}] 尝试重新连接...")

        # 关闭旧连接
        if self._ws_connection:
            try:
                await self._ws_connection.close()
            except Exception as e:
                logger.warning(f"关闭WebSocket连接失败: {e}")
            self._ws_connection = None

        self._connected = False

        # 等待后重试
        for attempt in range(5):
            if not self._running:
                return

            logger.info(f"尝试重新连接期货用户数据流 (尝试 {attempt + 1}/5)...")
            await asyncio.sleep(5)

            success = await self.start()
            if success:
                logger.info("期货用户数据流重连成功")
                if self._reconnect_callback:
                    await self._reconnect_callback()
                return

        logger.error("期货用户数据流重连失败，停止客户端")
        await self.stop()

    # ========== listenKey 管理 ==========

    async def _create_listen_key(self) -> Optional[str]:
        """创建 listenKey (Testnet)

        Returns:
            listenKey 字符串，失败返回 None
        """
        try:
            url = "https://demo-fapi.binance.com/fapi/v1/listenKey"

            headers = {"X-MBX-APIKEY": self._api_key}

            async with httpx.AsyncClient(proxy=self._proxy_url) as client:
                response = await client.post(url, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data.get("listenKey")

        except Exception as e:
            logger.error(f"创建期货 listenKey 失败: {e}")
            return None

    async def _renew_listen_key(self) -> bool:
        """续期 listenKey

        Returns:
            是否成功
        """
        if not self._listen_key:
            return False

        try:
            url = "https://demo-fapi.binance.com/fapi/v1/listenKey"

            headers = {"X-MBX-APIKEY": self._api_key}
            params = {"listenKey": self._listen_key}

            async with httpx.AsyncClient(proxy=self._proxy_url) as client:
                response = await client.put(
                    url, headers=headers, params=params, timeout=10.0
                )
                response.raise_for_status()
                return True

        except Exception as e:
            logger.error(f"续期期货 listenKey 失败: {e}")
            return False

    async def _close_listen_key(self, listen_key: str) -> None:
        """关闭 listenKey

        Args:
            listen_key: 要关闭的 listenKey
        """
        try:
            url = "https://demo-fapi.binance.com/fapi/v1/listenKey"

            headers = {"X-MBX-APIKEY": self._api_key}
            params = {"listenKey": listen_key}

            async with httpx.AsyncClient(proxy=self._proxy_url) as client:
                response = await client.delete(
                    url, headers=headers, params=params, timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"期货 listenKey 已关闭: {listen_key[:10]}...")

        except Exception as e:
            logger.warning(f"关闭期货 listenKey 失败: {e}")
