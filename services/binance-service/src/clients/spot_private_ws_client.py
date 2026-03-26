"""
现货私有WebSocket客户端（集成用户数据流）

支持Ed25519签名认证的现货私有WebSocket API客户端。
用于执行订单操作和接收用户数据流事件。

WebSocket端点：wss://demo-ws-api.binance.com/ws-api/v3 (仅Demo模式)

关键特性（设计文档 8.10.10）：
1. session.logon 会话级认证 - 认证后无需每个请求单独签名
2. 订单操作：order.place、order.cancel、order.status
3. 用户数据流订阅：subscribe_user_data_stream / unsubscribe_user_data_stream
4. 统一接口 - 与 FuturesPrivateWSClient 接口一致

现货用户数据流特点：
- 与API连接共用同一WebSocket连接
- 通过 userDataStream.subscribe 订阅
- 事件格式：{subscriptionId: 0, event: {...}}
- 事件类型：outboundAccountPosition, balanceUpdate, executionReport
"""

import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional

from clients.base_ws_client import WSDataPackage
from clients.session_auth_ws_client import SessionAuthWSClient
from utils.ed25519_signer import Ed25519Signer

logger = logging.getLogger(__name__)


class BinanceSpotPrivateWSClient(SessionAuthWSClient):
    """现货私有WebSocket客户端（会话级认证 + 用户数据流）

    继承 SessionAuthWSClient 统一设计：
    - start() = connect() + _do_session_logon()
    - stop() = 停止认证 + disconnect()
    - 子类实现 _do_session_logon() 完成 Ed25519 签名认证

    额外职责：
    - 用户数据流订阅（subscribe_user_data_stream / unsubscribe_user_data_stream）
    - 接收 outboundAccountPosition, balanceUpdate, executionReport 事件

    注意：现货用户数据流与API连接共用同一连接，通过 userDataStream.subscribe 订阅。
    不像期货那样需要独立的 listenKey 和数据流连接。

    Args:
        api_key: 币安API Key
        private_key_pem: Ed25519私钥（PEM格式）
        timeout: 请求超时时间（秒）
        proxy_url: 可选的代理URL
    """

    # 现货WebSocket端点 - 仅Demo模式，确保安全
    WS_URI = "wss://demo-ws-api.binance.com/ws-api/v3"
    CLIENT_ID = "binance-spot-private-ws-001"

    def __init__(
        self,
        api_key: str,
        private_key_pem: bytes,
        timeout: float = 5.0,
        proxy_url: Optional[str] = None,
    ) -> None:
        """初始化现货私有WebSocket客户端

        Args:
            api_key: 币安API Key
            private_key_pem: Ed25519私钥PEM格式
            timeout: 请求超时时间
            proxy_url: 可选的代理URL
        """
        super().__init__(proxy_url=proxy_url)

        self.api_key = api_key
        self._signer = Ed25519Signer(private_key_pem)
        self._timeout = timeout

        # 响应回调 - 回调模式核心（用于异步处理订单响应）
        self._response_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None

        # 请求 ID 计数器
        self._request_id_counter = 1000

        # ========== 用户数据流相关 ==========
        self._user_stream_subscribed: bool = False  # 是否已订阅
        self._user_stream_callback: Optional[Callable[[WSDataPackage], Awaitable[None]]] = None

    def set_response_callback(
        self, callback: Callable[[str, dict], Awaitable[None]]
    ) -> None:
        """设置响应回调

        Args:
            callback: 回调函数，签名为 (request_id: str, response: dict) -> Awaitable[None]
        """
        self._response_callback = callback
        logger.debug(f"[{self.CLIENT_ID}] 响应回调已设置")

    async def subscribe(self, request: Any = None) -> None:
        """订阅用户数据流（统一接口）

        实现 WSSubscriptionManager 统一订阅接口。
        用户数据流订阅在 session.logon 认证后通过此方法触发。

        Args:
            request: 忽略（用户数据流不需要 request 参数）
        """
        logger.info(f"[{self.CLIENT_ID}] 触发用户数据流订阅")
        # 调用内部的 subscribe_user_data_stream 完成订阅
        await self.subscribe_user_data_stream(callback=None)

    async def unsubscribe(self, request: Any = None) -> None:
        """取消订阅用户数据流（统一接口）

        实现 WSSubscriptionManager 统一取消订阅接口。

        Args:
            request: 忽略（用户数据流取消订阅不需要 request 参数）
        """
        logger.info(f"[{self.CLIENT_ID}] 触发用户数据流取消订阅")
        await self.unsubscribe_user_data_stream()

    async def send_request(self, method: str, params: dict, request_id: str) -> None:
        """发送请求（不等待响应，通过回调处理响应）

        session.logon 认证后，无需每个请求单独签名

        Args:
            method: WebSocket API方法名
            params: 请求参数
            request_id: 请求ID，用于关联响应
        """
        request = {
            "id": request_id,
            "method": method,
            "params": params,
        }

        await self._send(request)
        logger.debug(f"[{self.CLIENT_ID}] 请求已发送: method={method}, id={request_id}")

    def _next_request_id(self) -> str:
        """生成下一个请求 ID"""
        self._request_id_counter += 1
        return str(self._request_id_counter)

    # ========== session.logon 认证实现 ==========

    async def _do_session_logon(self) -> bool:
        """执行 session.logon 认证（Ed25519签名）

        流程：
        1. 构建 auth_params = {apiKey, timestamp}
        2. payload = "apiKey=xxx&timestamp=xxx"（按键排序）
        3. signature = self._signer.sign(payload)
        4. 发送 session.logon 请求
        5. 等待认证结果（使用 asyncio.Event 同步，超时 30s）

        Returns:
            认证是否成功
        """
        timestamp = int(time.time() * 1000)

        # 构建签名 payload：按键名字母顺序排序后用 & 连接
        auth_params = {
            "apiKey": self.api_key,
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
                "apiKey": self.api_key,
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

    async def _reconnect(self) -> None:
        """断线重连（覆盖基类实现）

        重连后重置会话认证状态，因为服务器可能已丢失会话。
        这确保下次 start() 调用时会重新认证。

        注意：期货使用独立的用户数据流连接，不需要这个修复。
        但现货用户数据流与 API 连接共用，必须处理会话失效问题。
        """
        # 先调用基类实现进行重连
        await super()._reconnect()

        # 重连成功后重置会话认证状态
        # 因为服务器可能已丢失会话，必须重新认证
        if self._running and self._state.connected:
            logger.info(f"[{self.CLIENT_ID}] 重连成功，重置会话认证状态")
            self._session_authenticated = False

    # ========== 用户数据流订阅接口 ==========

    async def subscribe_user_data_stream(
        self,
        callback: Callable[[WSDataPackage], Awaitable[None]],
    ) -> bool:
        """订阅用户数据流

        内部流程：
        1. 确保 session.logon 已认证（如果需要，重连并重新认证）
        2. 发送 userDataStream.subscribe 请求
        3. 监听账户事件，收到后调用 callback

        现货用户数据流与 API 连接共用同一 WebSocket 连接。
        事件格式：{subscriptionId: 0, event: {...}}
        事件类型：outboundAccountPosition, balanceUpdate, executionReport

        注意：如果 _session_authenticated 为 False（可能因断连重置），会自动重新认证。

        Args:
            callback: 数据回调函数，接收 WSDataPackage

        Returns:
            订阅是否成功
        """
        # 1. 确保 API 连接已认证
        if not self._session_authenticated:
            logger.info(f"[{self.CLIENT_ID}] session.logon 未认证，尝试重新认证...")
            # 检查连接状态
            if not self._state.connected:
                logger.warning(f"[{self.CLIENT_ID}] 连接已断开，尝试重连...")
                await self._reconnect()

            # 重新认证
            auth_success = await self._do_session_logon()
            if not auth_success:
                logger.error(f"[{self.CLIENT_ID}] 重新认证失败，无法订阅用户数据流")
                return False
            self._session_authenticated = True

        # 2. 如果已订阅，先取消
        if self._user_stream_subscribed:
            logger.info(f"[{self.CLIENT_ID}] 已订阅，先取消再重新订阅")
            await self.unsubscribe_user_data_stream()

        # 3. 设置数据回调
        self._user_stream_callback = callback

        # 4. 发送订阅请求
        subscribe_request = {
            "id": self._next_request_id(),
            "method": "userDataStream.subscribe",
            "params": {},
        }

        logger.info(f"[{self.CLIENT_ID}] 正在订阅 userDataStream...")
        await self._send(subscribe_request)

        self._user_stream_subscribed = True
        logger.info(f"[{self.CLIENT_ID}] userDataStream 订阅请求已发送")
        return True

    async def unsubscribe_user_data_stream(self) -> None:
        """取消订阅用户数据流

        关闭订阅，但不关闭 session（保持 session.logon 有效）。
        """
        if not self._user_stream_subscribed:
            logger.debug(f"[{self.CLIENT_ID}] 未订阅用户数据流，无需取消")
            return

        logger.info(f"[{self.CLIENT_ID}] 正在取消订阅用户数据流...")

        # 发送取消订阅请求
        unsubscribe_request = {
            "id": self._next_request_id(),
            "method": "userDataStream.unsubscribe",
            "params": {},
        }

        await self._send(unsubscribe_request)

        self._user_stream_subscribed = False
        self._user_stream_callback = None
        logger.info(f"[{self.CLIENT_ID}] 用户数据流取消订阅完成")

    # ========== 消息处理 ==========

    async def _handle_message(self, message: dict) -> None:
        """处理接收收到的消息

        会话级认证模式：处理 session.logon 响应、订单响应、用户数据流事件

        Args:
            message: 消息数据
        """
        logger.debug(f"[{self.CLIENT_ID}] 收到消息: {json.dumps(message)[:500]}")

        # 1. 识别 session.logon 成功响应
        # 响应格式：{"id": "...", "status": 200, "result": {"apiKey": "...", "userDataStream": false}}
        if "status" in message and message.get("status") == 200 and "result" in message:
            result = message.get("result")
            if isinstance(result, dict) and "apiKey" in result:
                if self._auth_event and not self._auth_event.is_set():
                    self._auth_success = True
                    self._auth_event.set()
                    logger.debug(f"[{self.CLIENT_ID}] session.logon 响应已处理")
                return

        # 2. 识别错误消息
        if "status" in message and message.get("status") != 200:
            error_code = message.get("error", {}).get("code", "unknown")
            error_msg = message.get("error", {}).get("msg", "unknown")
            logger.debug(f"[{self.CLIENT_ID}] WebSocket 错误: code={error_code}, msg={error_msg}")

            # 检查是否是 session.logon 认证失败
            if error_code == -1193 or "session not authenticated" in error_msg.lower():
                if self._auth_event and not self._auth_event.is_set():
                    self._auth_success = False
                    self._auth_event.set()
                    logger.debug(f"[{self.CLIENT_ID}] session.logon 认证失败")
            return

        # 3. 识别响应消息（包含id和result/status）
        if "id" in message and ("result" in message or "status" in message):
            request_id = str(message["id"])
            logger.debug(f"[{self.CLIENT_ID}] 收到响应消息, id={request_id}")

            # 使用回调模式处理响应
            if self._response_callback:
                await self._response_callback(request_id, message)
                logger.debug(f"[{self.CLIENT_ID}] 响应已通过回调处理: id={request_id}")
            else:
                logger.debug(f"[{self.CLIENT_ID}] 收到未知请求的响应: id={request_id}")
            return

        # 4. 处理用户数据流事件
        # 现货事件格式：{"subscriptionId": 0, "event": {...}}
        if "subscriptionId" in message and "event" in message:
            await self._handle_user_stream_message(message)
            return

        # 5. 处理其他消息（如订阅确认）
        if "subscriptionId" in message or "sessionId" in message:
            logger.debug(f"[{self.CLIENT_ID}] 订阅/会话消息: {message}")
            return

        # 其他未知消息
        logger.debug(f"[{self.CLIENT_ID}] 收到其他消息: {message.get('e', 'unknown')}")

    async def _handle_user_stream_message(self, message: dict) -> None:
        """处理用户数据流消息

        现货用户数据流事件格式：
        {"subscriptionId": 0, "event": {"e": "...", ...}}

        事件类型：
        - outboundAccountPosition: 账户位置更新
        - balanceUpdate: 余额更新
        - executionReport: 订单执行报告

        重要：调用 self._data_callback（由 WSSubscriptionManager 设置）来路由数据。
        如果需要直接回调（如单元测试），可以通过 subscribe_user_data_stream 设置 _user_stream_callback。

        Args:
            message: 消息数据
        """
        event_data = message.get("event", {})
        event_type = event_data.get("e", "unknown")
        logger.info(f"[{self.CLIENT_ID}] 收到用户数据流事件: {event_type}")

        # 打包数据
        package = WSDataPackage(
            client_id=self.CLIENT_ID,
            data=message,
            timestamp=int(time.time() * 1000),
        )

        # 优先使用 _data_callback（由 WSSubscriptionManager 设置）
        # 这样数据会通过 WSSubscriptionManager._handle_data_package 路由
        if self._data_callback:
            await self._data_callback(package)
        elif self._user_stream_callback:
            # 回退到直接回调（用于单元测试等场景）
            await self._user_stream_callback(package)
        else:
            logger.warning(f"[{self.CLIENT_ID}] 用户数据流回调未设置，事件被忽略: {event_type}")
