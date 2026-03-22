"""
现货用户数据流客户端 (WebSocket API 方式)

设计原则：
- WS客户端只负责连接和接收数据
- 收到数据后立即打包为 WSDataPackage，发送给币安服务
- 不维护任何回调或订阅状态
- 所有数据处理由币安服务统一完成

职责划分：
- SpotUserStreamClient: 连接 + session.logon 认证
- WSManager: 决定何时发送 userDataStream.subscribe

特殊流程：
1. 连接 WebSocket API
2. session.logon 认证（Ed25519 签名，建立会话）
3. 接收事件并打包发送

端点: wss://demo-ws-api.binance.com/ws-api/v3 (仅 Demo 模式)

文档: https://docs.binance.com/binance-spot-api-docs/websocket-api/user-data-stream-requests
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Awaitable, Optional

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from clients.base_ws_client import WSDataPackage
from utils.ed25519_signer import Ed25519Signer

logger = logging.getLogger(__name__)


class SpotUserStreamClient:
    """现货用户数据流客户端 (WebSocket API 方式)

    职责：
    - 建立 WebSocket 连接
    - 执行 session.logon 认证
    - 接收消息并通过回调传递给调用方

    不负责：
    - 订阅管理（由 WSManager 控制）
    - 重连后的订阅恢复（由 WSManager 触发）
    """

    # 现货 WebSocket API 端点 - 仅 Demo 模式
    WS_URI = "wss://demo-ws-api.binance.com/ws-api/v3"
    CLIENT_ID = "binance-spot-user-stream-001"

    def __init__(
        self,
        api_key: str,
        private_key_pem: bytes,
        signature_type: str = "ed25519",
        proxy_url: Optional[str] = None,
    ) -> None:
        """初始化现货用户数据流客户端

        Args:
            api_key: 币安 API Key
            private_key_pem: Ed25519 私钥（PEM 格式）
            signature_type: 签名类型（仅支持 ed25519）
            proxy_url: 可选的代理 URL
        """
        self._api_key = api_key
        self._signer = Ed25519Signer(private_key_pem)
        self._signature_type = signature_type
        self._proxy_url = proxy_url

        # WebSocket 连接
        self._websocket: Optional[Any] = None
        self._connected: bool = False
        self._running: bool = False

        # 任务引用
        self._receive_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None

        # 回调
        self._data_callback: Optional[Callable[[WSDataPackage], Awaitable[None]]] = None
        self._reconnect_callback: Optional[Callable[[], Awaitable[None]]] = None

        # 请求 ID 计数器
        self._request_id_counter = 1000

        # 认证状态同步
        self._auth_event: Optional[asyncio.Event] = None
        self._auth_success: bool = False

    def set_data_callback(self, callback: Callable[[WSDataPackage], Awaitable[None]]) -> None:
        """设置数据回调"""
        self._data_callback = callback

    def set_reconnect_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """设置断线重连回调"""
        self._reconnect_callback = callback

    def _next_request_id(self) -> str:
        """生成下一个请求 ID"""
        self._request_id_counter += 1
        return str(self._request_id_counter)

    async def connect(self) -> None:
        """建立 WebSocket 连接并完成认证

        流程：
        1. 连接 WebSocket API
        2. session.logon 认证

        注意：不自动订阅，订阅由 WSManager 通过 subscribe() 方法触发
        """
        if self._connected:
            logger.info(f"[{self.CLIENT_ID}] 已连接，跳过")
            return

        logger.info(f"[{self.CLIENT_ID}] 正在连接...")
        try:
            connect_kwargs: dict[str, Any] = {}
            if self._proxy_url:
                connect_kwargs["proxy"] = self._proxy_url

            self._websocket = await connect(self.WS_URI, **connect_kwargs)
            self._connected = True
            self._running = True
            logger.info(f"[{self.CLIENT_ID}] WebSocket 连接已建立")

            # 先启动接收循环，用于处理认证响应
            self._receive_task = asyncio.create_task(self._receive_loop())

            # session.logon 认证（等待认证结果）
            auth_success = await self._session_logon()
            if not auth_success:
                logger.error(f"[{self.CLIENT_ID}] session.logon 认证失败，断开连接并重试")
                await self.disconnect()
                self._schedule_reconnect()
                return

        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 连接失败: {e}")
            self._connected = False
            self._running = True
            self._schedule_reconnect()

    async def _session_logon(self) -> bool:
        """执行 session.logon 认证

        Ed25519 签名 payload 格式：apiKey=xxx&timestamp=xxx（按键名字母排序）

        Returns:
            认证是否成功
        """
        timestamp = int(time.time() * 1000)

        # 构建签名 payload：按键名字母顺序排序后用 & 连接
        auth_params = {
            "apiKey": self._api_key,
            "timestamp": timestamp,
        }
        sorted_params = dict(sorted(auth_params.items()))
        payload = "&".join(f"{k}={v}" for k, v in sorted_params.items())

        # Ed25519 签名
        signature = self._signer.sign(payload)

        # 创建认证事件用于同步
        self._auth_event = asyncio.Event()
        self._auth_success = False

        # 构建认证请求
        auth_request = {
            "id": self._next_request_id(),
            "method": "session.logon",
            "params": {
                "apiKey": self._api_key,
                "timestamp": timestamp,
                "signature": signature,
            },
        }

        logger.info(f"[{self.CLIENT_ID}] 正在执行 session.logon 认证...")
        await self._send(auth_request)
        logger.info(f"[{self.CLIENT_ID}] session.logon 请求已发送，等待认证结果...")

        # 等待认证结果（最多30秒超时）
        try:
            await asyncio.wait_for(self._auth_event.wait(), timeout=30)
        except asyncio.TimeoutError:
            logger.error(f"[{self.CLIENT_ID}] session.logon 认证超时")
            return False

        if self._auth_success:
            logger.info(f"[{self.CLIENT_ID}] session.logon 认证成功")
        else:
            logger.error(f"[{self.CLIENT_ID}] session.logon 认证失败")

        return self._auth_success

    async def subscribe(self) -> bool:
        """订阅用户数据流

        由 WSManager 调用，在连接和认证完成后触发订阅。

        Returns:
            是否订阅成功
        """
        if not self._connected:
            logger.warning(f"[{self.CLIENT_ID}] 未连接，无法订阅")
            return False

        subscribe_request = {
            "id": self._next_request_id(),
            "method": "userDataStream.subscribe",
            "params": {},
        }

        logger.info(f"[{self.CLIENT_ID}] 正在订阅 userDataStream...")
        await self._send(subscribe_request)
        logger.info(f"[{self.CLIENT_ID}] userDataStream.subscribe 请求已发送")
        return True

    async def _send(self, message: dict) -> None:
        """发送消息"""
        if self._websocket:
            await self._websocket.send(json.dumps(message))

    async def _receive_loop(self) -> None:
        """接收消息循环"""
        try:
            while self._running and self._connected:
                try:
                    message = await asyncio.wait_for(
                        self._websocket.recv(), timeout=1.0
                    )
                    data = json.loads(message)
                    await self._handle_message(data)
                except asyncio.TimeoutError:
                    continue
                except ConnectionClosed:
                    logger.warning(f"[{self.CLIENT_ID}] 连接已关闭")
                    break
                except Exception as e:
                    logger.error(f"[{self.CLIENT_ID}] 接收消息异常: {e}")
                    break
        except asyncio.CancelledError:
            logger.info(f"[{self.CLIENT_ID}] 接收循环已取消")
        finally:
            if self._connected:
                self._connected = False
                if self._running:
                    self._schedule_reconnect()

    async def _handle_message(self, message: dict) -> None:
        """处理接收到的消息

        业务事件消息（outboundAccountPosition, balanceUpdate, executionReport 等）
        格式：{"subscriptionId": 0, "event": {...}}
        """
        # 识别 session.logon 成功响应
        # 响应格式：{"id": "...", "status": 200, "result": {"apiKey": "...", "userDataStream": false}}
        if "status" in message and message.get("status") == 200 and "result" in message:
            result = message.get("result")
            # session.logon 成功的响应包含 apiKey
            if isinstance(result, dict) and "apiKey" in result:
                if self._auth_event and not self._auth_event.is_set():
                    self._auth_success = True
                    self._auth_event.set()
            return

        # 识别错误消息
        if "status" in message and message.get("status") != 200:
            error_code = message.get("error", {}).get("code", "unknown")
            error_msg = message.get("error", {}).get("msg", "unknown")
            logger.error(f"[{self.CLIENT_ID}] WebSocket 错误: code={error_code}, msg={error_msg}")

            # 检查是否是 session.logon 认证失败
            if error_code == -1193 or "session not authenticated" in error_msg.lower():
                if self._auth_event and not self._auth_event.is_set():
                    self._auth_success = False
                    self._auth_event.set()
                    logger.error(f"[{self.CLIENT_ID}] session.logon 认证失败")
            return

        # 识别会话状态消息
        if "sessionId" in message or "status" in message:
            logger.debug(f"[{self.CLIENT_ID}] 会话状态消息: {message}")
            return

        # 业务事件消息
        if "subscriptionId" in message and "event" in message:
            event_data = message.get("event", {})
            event_type = event_data.get("e", "unknown")
            logger.info(f"[{self.CLIENT_ID}] 收到业务事件: {event_type}")

            # 打包数据并发送给币安服务
            package = WSDataPackage(
                client_id=self.CLIENT_ID,
                data=message,
                timestamp=int(time.time() * 1000),
            )

            if self._data_callback:
                await self._data_callback(package)
            return

        # 其他消息类型
        logger.debug(f"[{self.CLIENT_ID}] 收到其他消息: {message}")

    def _schedule_reconnect(self) -> None:
        """调度延迟重连"""
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()

        async def reconnect_loop():
            delay = 2
            while self._running and not self._connected:
                logger.info(f"[{self.CLIENT_ID}] 等待 {delay} 秒后重试...")
                await asyncio.sleep(delay)
                if not self._running:
                    break

                logger.info(f"[{self.CLIENT_ID}] 尝试重新连接...")
                try:
                    # 关闭旧连接
                    if self._websocket:
                        try:
                            await self._websocket.close()
                        except Exception:
                            pass
                    self._websocket = None

                    # 创建新连接
                    connect_kwargs: dict[str, Any] = {}
                    if self._proxy_url:
                        connect_kwargs["proxy"] = self._proxy_url

                    self._websocket = await connect(self.WS_URI, **connect_kwargs)
                    self._connected = True
                    logger.info(f"[{self.CLIENT_ID}] 已重新连接")

                    # 重新认证
                    await self._session_logon()

                    # 重启接收循环
                    self._receive_task = asyncio.create_task(self._receive_loop())

                    # 通知上层重连完成，以便重新订阅
                    if self._reconnect_callback:
                        await self._reconnect_callback()

                    logger.info(f"[{self.CLIENT_ID}] 重连任务完成")
                    return

                except Exception as e:
                    logger.error(f"[{self.CLIENT_ID}] 重连失败: {e}")
                    self._connected = False
                    delay = min(delay * 2, 60)  # 指数退避，最大60秒

        self._reconnect_task = asyncio.create_task(reconnect_loop())

    async def disconnect(self) -> None:
        """断开 WebSocket 连接"""
        logger.info(f"[{self.CLIENT_ID}] 正在断开连接...")
        self._running = False

        # 重置认证状态
        self._auth_event = None
        self._auth_success = False

        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass
            self._websocket = None

        self._connected = False
        logger.info(f"[{self.CLIENT_ID}] 连接已断开")

    @property
    def is_connected(self) -> bool:
        return self._connected
