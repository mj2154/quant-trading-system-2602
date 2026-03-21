"""
现货用户数据流客户端 (WebSocket API 方式)

设计原则（与 BaseWSClient 一致）：
- WS客户端只负责连接和接收数据
- 收到数据后立即打包为 WSDataPackage，发送给币安服务
- 不维护任何回调或订阅状态
- 所有数据处理由币安服务统一完成

特殊流程：
1. 连接 WebSocket API
2. session.logon 认证（Ed25519 签名，建立会话）
3. userDataStream.subscribe 订阅账户数据流
4. 接收事件并打包发送

端点: wss://demo-ws-api.binance.com/ws-api/v3 (仅 Demo 模式)

文档: https://docs.binance.com/binance-spot-api-docs/websocket-api/user-data-stream-requests
"""

import asyncio
import json
import logging
import time
from typing import Any, Optional

from websockets.asyncio.client import connect

from clients.base_ws_client import BaseWSClient, WSDataPackage
from utils.ed25519_signer import Ed25519Signer

logger = logging.getLogger(__name__)


class SpotUserStreamClient(BaseWSClient):
    """现货用户数据流客户端 (WebSocket API 方式)

    继承 BaseWSClient，统一客户端模式：
    - connect() -> 建立连接
    - disconnect() -> 断开连接
    - 接收数据 -> 打包为 WSDataPackage -> 调用 _data_callback

    特殊流程：
    - session.logon 认证（Ed25519 签名）
    - userDataStream.subscribe 订阅账户数据流

    会话级认证特点：
    - 无需每个请求都签名
    - 无需 listenKey
    - 无需续期
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
        super().__init__(proxy_url=proxy_url)

        self._api_key = api_key
        self._signer = Ed25519Signer(private_key_pem)
        self._signature_type = signature_type

        # 请求 ID 计数器
        self._request_id_counter = 1000

        # 订阅 ID（用于追踪订阅）
        self._subscription_id: Optional[int] = None

    def _next_request_id(self) -> str:
        """生成下一个请求 ID"""
        self._request_id_counter += 1
        return str(self._request_id_counter)

    async def connect(self) -> None:
        """建立 WebSocket 连接并完成认证

        流程：
        1. 连接 WebSocket API
        2. session.logon 认证
        3. userDataStream.subscribe 订阅
        """
        if self._state.connected:
            logger.info(f"[{self.CLIENT_ID}] 已连接，跳过")
            return

        logger.info(f"[{self.CLIENT_ID}] 正在连接...")
        try:
            connect_kwargs: dict[str, Any] = {}
            if self._proxy_url:
                connect_kwargs["proxy"] = self._proxy_url

            self._websocket = await connect(self.WS_URI, **connect_kwargs)
            self._state.connected = True
            self._running = True
            logger.info(f"[{self.CLIENT_ID}] WebSocket 连接已建立")

            # 启动接收循环
            self._receive_task = asyncio.create_task(self._receive_loop())

            # session.logon 认证
            await self._session_logon()

            # userDataStream.subscribe 订阅
            await self._subscribe_user_data_stream()

        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 连接失败: {e}")
            self._state.connected = False
            self._running = True
            # 调度持续重连
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
            self._reconnect_task = asyncio.create_task(self._schedule_reconnect())

    async def _session_logon(self) -> None:
        """执行 session.logon 认证

        Ed25519 签名 payload 格式：apiKey=xxx&timestamp=xxx（按键名字母排序）
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

        # 注意：BaseWSClient 的 _receive_loop 会处理响应
        # 响应会通过 _handle_message 处理
        logger.info(f"[{self.CLIENT_ID}] session.logon 请求已发送")

    async def _subscribe_user_data_stream(self) -> None:
        """订阅用户数据流"""
        subscribe_request = {
            "id": self._next_request_id(),
            "method": "userDataStream.subscribe",
            "params": {},
        }

        logger.info(f"[{self.CLIENT_ID}] 正在订阅 userDataStream...")
        await self._send(subscribe_request)
        logger.info(f"[{self.CLIENT_ID}] userDataStream.subscribe 请求已发送")

    async def _handle_message(self, message: dict) -> None:
        """处理接收到的消息

        BaseWSClient 模式：
        - 收到数据后立即打包为 WSDataPackage
        - 调用 _data_callback 发送给币安服务
        - 不做任何数据解析
        """
        # 识别 ACK 确认消息 {"result": null, "id": xxx}
        if "result" in message and "id" in message:
            result = message.get("result")
            request_id = message.get("id")
            logger.debug(
                f"[{self.CLIENT_ID}] 收到 ACK 确认: result={result}, id={request_id}"
            )

            # 如果是订阅响应，记录 subscriptionId
            if isinstance(result, dict) and "subscriptionId" in result:
                self._subscription_id = result.get("subscriptionId")
                logger.info(
                    f"[{self.CLIENT_ID}] 订阅成功: subscriptionId={self._subscription_id}"
                )
            return

        # 识别错误消息
        if "status" in message and message.get("status") != 200:
            error_code = message.get("error", {}).get("code", "unknown")
            error_msg = message.get("error", {}).get("msg", "unknown")
            logger.error(f"[{self.CLIENT_ID}] WebSocket 错误: code={error_code}, msg={error_msg}")
            return

        # 识别会话状态消息
        if "sessionId" in message or "status" in message:
            logger.debug(f"[{self.CLIENT_ID}] 会话状态消息: {message}")
            return

        # 业务事件消息（outboundAccountPosition, balanceUpdate, executionReport 等）
        # 格式：{"subscriptionId": 0, "event": {...}}
        if "subscriptionId" in message and "event" in message:
            event_data = message.get("event", {})
            event_type = event_data.get("e", "unknown")
            logger.debug(f"[{self.CLIENT_ID}] 收到业务事件: {event_type}")

            # 打包数据并发送给币安服务（不解析）
            package = WSDataPackage(
                client_id=self.CLIENT_ID,
                data=message,  # 发送原始消息，不解析
                timestamp=int(time.time() * 1000),
            )

            if self._data_callback:
                await self._data_callback(package)
            return

        # 其他消息类型
        logger.debug(f"[{self.CLIENT_ID}] 收到其他消息: {message}")

    async def _reconnect(self) -> None:
        """断线重连

        重连后需要重新：
        1. 连接 WebSocket
        2. session.logon 认证
        3. userDataStream.subscribe 订阅
        """
        if not self._running:
            return

        logger.info(f"[{self.CLIENT_ID}] 尝试重新连接...")

        # 1. 正确关闭旧连接
        old_websocket = self._websocket
        self._websocket = None
        self._state.connected = False
        self._subscription_id = None

        if old_websocket:
            try:
                await old_websocket.close()
                logger.debug(f"[{self.CLIENT_ID}] 旧连接已关闭")
            except Exception as e:
                logger.warning(f"[{self.CLIENT_ID}] 关闭旧连接时出错: {e}")

        # 2. 尝试创建新连接
        success = await self._try_reconnect()

        if success and self._running:
            # 重新认证和订阅
            await self._session_logon()
            await self._subscribe_user_data_stream()

            # 通知上层重连完成
            if self._reconnect_callback:
                await self._reconnect_callback()
        elif not success and self._running:
            # 调度持续重试任务
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
            self._reconnect_task = asyncio.create_task(self._schedule_reconnect())

    async def _try_reconnect(self) -> bool:
        """尝试重连，返回是否成功"""
        try:
            # 关闭旧连接
            old_websocket = self._websocket
            self._websocket = None
            self._state.connected = False

            if old_websocket:
                try:
                    await old_websocket.close()
                except Exception as e:
                    logger.warning(f"[{self.CLIENT_ID}] 关闭旧连接时出错: {e}")

            # 创建新连接
            connect_kwargs: dict[str, Any] = {}
            if self._proxy_url:
                connect_kwargs["proxy"] = self._proxy_url

            self._websocket = await connect(self.WS_URI, **connect_kwargs)
            self._state.connected = True
            logger.info(f"[{self.CLIENT_ID}] 已重新连接")

            self._receive_task = asyncio.create_task(self._receive_loop())
            self._reconnect_task = None
            return True

        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 重连失败: {e}")
            self._state.connected = False
            return False
