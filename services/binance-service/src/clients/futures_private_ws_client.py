"""
期货私有WebSocket客户端

会话级认证的期货私有WebSocket API客户端。

WebSocket端点：wss://testnet.binancefuture.com/ws-fapi/v1 (仅Testnet)

关键特性：
1. session.logon 会话级认证 - 认证后24小时内无需重复签名
2. listenKey 管理 - 创建/续期/关闭
3. 用户数据流订阅 - 接收 ACCOUNT_UPDATE, ORDER_TRADE_UPDATE 事件
4. Ed25519 签名认证
5. 统一接口 - subscribe_user_data_stream() / unsubscribe_user_data_stream()
"""

import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from clients.base_ws_client import WSDataPackage
from clients.session_auth_ws_client import SessionAuthWSClient
from utils.ed25519_signer import Ed25519Signer

logger = logging.getLogger(__name__)


class BinanceFuturesPrivateWSClient(SessionAuthWSClient):
    """期货私有WebSocket客户端（会话级认证 + 用户数据流）

    继承 SessionAuthWSClient 统一设计：
    - start() = connect() + _do_session_logon()
    - stop() = 停止认证 + disconnect()
    - 子类实现 _do_session_logon() 完成 Ed25519 签名认证

    额外职责：
    - listenKey 管理（创建/续期/关闭）
    - 用户数据流订阅（subscribe_user_data_stream / unsubscribe_user_data_stream）
    - 接收 ACCOUNT_UPDATE, ORDER_TRADE_UPDATE, listenKeyExpired 事件

    内部架构：
    - API 连接：用于 session.logon 和各种 WS API 调用
    - 用户数据流连接：专门用于接收账户更新，listenKey 由 API 连接管理

    Args:
        api_key: 币安API Key
        private_key_pem: Ed25519私钥（PEM格式）
        timeout: 请求超时时间（秒）
        proxy_url: 可选的代理URL
        use_testnet: 是否使用测试网（默认True）
    """

    # 期货WebSocket端点 - 仅Testnet，生产网地址暂时禁用
    WS_URI = None  # 生产网已禁用，请勿填写
    TESTNET_WS_URI = "wss://testnet.binancefuture.com/ws-fapi/v1"
    CLIENT_ID = "binance-futures-private-ws-001"

    # 用户数据流 WebSocket 端点（Testnet）
    USER_STREAM_WS_URI = "wss://fstream.binancefuture.com/ws"

    # listenKey 续期间隔（55分钟，提前5分钟续期）
    LISTEN_KEY_RENEW_INTERVAL = 55 * 60

    def __init__(
        self,
        api_key: str,
        private_key_pem: bytes,
        timeout: float = 5.0,
        proxy_url: Optional[str] = None,
        use_testnet: bool = True,
    ) -> None:
        """初始化私有WebSocket客户端

        Args:
            api_key: 币安API Key
            private_key_pem: Ed25519私钥PEM格式
            timeout: 请求超时时间
            proxy_url: 可选的代理URL
            use_testnet: 是否使用测试网（默认True）
        """
        # 设置WebSocket URI - 生产网已禁用，必须使用Testnet
        if use_testnet:
            ws_uri = self.TESTNET_WS_URI
        else:
            raise ValueError("生产网已禁用，请勿设置为False")

        super().__init__(proxy_url=proxy_url)

        # 覆盖基类的URI
        self.WS_URI = ws_uri

        self.api_key = api_key
        self._signer = Ed25519Signer(private_key_pem)
        self._timeout = timeout

        # 响应回调 - 回调模式核心（用于异步处理订单响应）
        self._response_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None

        # listenKey 管理
        self._listen_key: Optional[str] = None
        self._listen_key_event: Optional[asyncio.Event] = None  # listenKey 响应同步事件
        self._listen_key_renew_task: Optional[asyncio.Task] = None
        self._pending_listen_key_request_id: Optional[str] = None  # 等待中的 listenKey 管理请求 ID

        # 请求 ID 计数器
        self._request_id_counter = 2000

        # ========== 用户数据流相关（独立连接）==========
        # 用户数据流 WebSocket 连接
        self._user_stream_websocket: Any = None
        self._user_stream_connected: bool = False
        self._user_stream_running: bool = False
        self._user_stream_receive_task: Optional[asyncio.Task] = None
        self._user_stream_subscribed: bool = False  # 是否已订阅

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

        注意：期货用户数据流使用独立的 WebSocket 连接（fstream.binancefuture.com），
        内部通过 listenKey 管理连接。

        Args:
            request: 忽略（用户数据流不需要 request 参数）
        """
        logger.info(f"[{self.CLIENT_ID}] 触发用户数据流订阅")
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

        会话级认证模式下，无需每个请求单独签名

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

    async def _do_session_logon(self) -> bool:
        """执行 session.logon 认证（Ed25519签名）

        与 SpotUserStreamClient 类似：
        1. 构建 auth_params = {apiKey, timestamp}
        2. payload = "apiKey=xxx&timestamp=xxx"（按键排序）
        3. signature = self._signer.sign(payload)
        4. 发送 session.logon 请求
        5. 等待认证结果（使用 asyncio.Event 同步）

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
            self._session_authenticated = True
        else:
            logger.error(f"[{self.CLIENT_ID}] session.logon 认证失败")

        return self._auth_success

    async def _create_listen_key(self) -> Optional[str]:
        """创建 listenKey（带 Event 同步等待）

        使用 asyncio.Event 等待 _handle_message 设置 listenKey

        Returns:
            创建的 listenKey，失败返回 None
        """
        logger.info(f"[{self.CLIENT_ID}] 创建 listenKey...")

        # 构建请求 - userDataStream.start 只接受 apiKey 参数
        request_id = self._next_request_id()
        request = {
            "id": request_id,
            "method": "userDataStream.start",
            "params": {
                "apiKey": self.api_key,
            },
        }

        # 创建同步事件用于等待响应
        self._listen_key_event = asyncio.Event()
        self._listen_key = None

        await self._send(request)

        # 等待 listenKey 响应（最多30秒超时）
        try:
            await asyncio.wait_for(self._listen_key_event.wait(), timeout=30)
            listen_key = self._listen_key
            if listen_key:
                logger.info(f"[{self.CLIENT_ID}] listenKey 创建成功: {listen_key[:10]}...")
            else:
                logger.error(f"[{self.CLIENT_ID}] listenKey 创建失败: 响应中未包含 listenKey")
            return listen_key
        except asyncio.TimeoutError:
            logger.error(f"[{self.CLIENT_ID}] listenKey 创建超时")
            return None
        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] listenKey 创建异常: {e}")
            return None
        finally:
            self._listen_key_event = None

    async def _renew_listen_key(self) -> bool:
        """续期 listenKey

        Returns:
            续期是否成功
        """
        if not self._listen_key:
            logger.warning(f"[{self.CLIENT_ID}] 无 listenKey 可续期")
            return False

        # 构建请求 - userDataStream.ping 只接受 apiKey 参数
        request_id = self._next_request_id()
        request = {
            "id": request_id,
            "method": "userDataStream.ping",
            "params": {
                "apiKey": self.api_key,
            },
        }

        # 标记为待处理的 listenKey 管理请求（响应由 WS 客户端自己处理）
        self._pending_listen_key_request_id = request_id

        logger.debug(f"[{self.CLIENT_ID}] 续期 listenKey: {self._listen_key[:10]}...")
        await self._send(request)
        return True

    async def _stop_listen_key(self) -> None:
        """关闭 listenKey（内部方法）"""
        if not self._listen_key:
            logger.warning(f"[{self.CLIENT_ID}] 无 listenKey 可关闭")
            return

        # 构建请求 - userDataStream.stop 只接受 apiKey 参数
        request_id = self._next_request_id()
        old_listen_key = self._listen_key
        request = {
            "id": request_id,
            "method": "userDataStream.stop",
            "params": {
                "apiKey": self.api_key,
            },
        }

        # 标记为待处理的 listenKey 管理请求（响应由 WS 客户端自己处理）
        self._pending_listen_key_request_id = request_id

        logger.info(f"[{self.CLIENT_ID}] 关闭 listenKey: {old_listen_key[:10]}...")
        await self._send(request)
        self._listen_key = None

    async def _listen_key_renew_loop(self) -> None:
        """listenKey 续期循环

        每55分钟续期一次，提前5分钟避免过期
        """
        logger.info(f"[{self.CLIENT_ID}] listenKey 续期循环启动，间隔 {self.LISTEN_KEY_RENEW_INTERVAL / 60} 分钟")

        while self._running and self._listen_key:
            try:
                await asyncio.sleep(self.LISTEN_KEY_RENEW_INTERVAL)
                if not self._running or not self._listen_key:
                    break
                await self._renew_listen_key()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.CLIENT_ID}] listenKey 续期异常: {e}")

        logger.info(f"[{self.CLIENT_ID}] listenKey 续期循环结束")

    # ========== 公共 listenKey 管理接口（供 BinanceService 调用）==========

    async def create_listen_key(self) -> Optional[str]:
        """创建 listenKey（公共接口，供 BinanceService 调用）

        Returns:
            创建的 listenKey，失败返回 None
        """
        return await self._create_listen_key()

    async def renew_listen_key(self) -> bool:
        """续期 listenKey（公共接口，供 BinanceService 调用）

        Returns:
            续期是否成功
        """
        return await self._renew_listen_key()

    async def stop_listen_key(self) -> None:
        """关闭 listenKey（公共接口，供 BinanceService 调用）

        通过 userDataStream.stop WebSocket API 关闭 listenKey。
        """
        return await self._stop_listen_key()

    def get_listen_key(self) -> Optional[str]:
        """获取当前 listenKey

        Returns:
            当前 listenKey，如果不存在返回 None
        """
        return self._listen_key

    async def stop(self) -> None:
        """停止客户端

        流程：
        1. 停止用户数据流（如果正在运行）
        2. 停止续期循环（如果存在）
        3. 调用父类停止（重置认证状态 + 断开连接）

        注意：listenKey 的关闭由 BinanceService 统一调度，不再在此自动关闭
        """
        logger.info(f"[{self.CLIENT_ID}] 正在停止客户端...")

        # 1. 停止用户数据流
        await self._stop_user_stream()

        # 2. 停止续期循环（如果存在）
        self._running = False
        if self._listen_key_renew_task:
            self._listen_key_renew_task.cancel()
            try:
                await self._listen_key_renew_task
            except asyncio.CancelledError:
                pass
            self._listen_key_renew_task = None

        # 3. 调用父类停止（重置认证状态 + 断开连接）
        await super().stop()

        # 注意：保留 _listen_key，因为 BinanceService 可能在其他地方管理它

    # ========== 用户数据流订阅接口 ==========

    async def subscribe_user_data_stream(
        self,
        callback: Callable[[WSDataPackage], Awaitable[None]] | None = None,
    ) -> bool:
        """订阅用户数据流

        内部流程：
        1. 确保 API 连接已认证
        2. 创建 listenKey（如果没有）
        3. 建立用户数据流 WS 连接
        4. 启动自动续期循环（listenKey 每55分钟续期）
        5. 监听账户更新事件

        注意：数据回调通过 _data_callback 转发，由 WSSubscriptionManager 设置。
        当收到 listenKeyExpired 事件时，调用 _reconnect_callback()
        通知 BinanceService 执行 full_sync() 重新订阅。

        Returns:
            订阅是否成功
        """
        if not self._session_authenticated:
            logger.error(f"[{self.CLIENT_ID}] API 连接未认证，无法订阅用户数据流")
            return False

        # 如果已订阅，先取消
        if self._user_stream_subscribed:
            logger.info(f"[{self.CLIENT_ID}] 已订阅，先取消再重新订阅")
            await self.unsubscribe_user_data_stream()

        # 创建 listenKey
        listen_key = await self._create_listen_key()
        if not listen_key:
            logger.error(f"[{self.CLIENT_ID}] listenKey 创建失败，无法订阅用户数据流")
            return False

        # 建立用户数据流连接
        success = await self._start_user_stream(listen_key)
        if not success:
            logger.error(f"[{self.CLIENT_ID}] 用户数据流连接失败")
            return False

        # 启动 listenKey 续期循环
        self._listen_key_renew_task = asyncio.create_task(self._listen_key_renew_loop())

        self._user_stream_subscribed = True
        logger.info(f"[{self.CLIENT_ID}] 用户数据流订阅成功")
        return True

    async def unsubscribe_user_data_stream(self) -> None:
        """取消订阅用户数据流

        内部流程：
        1. 停止续期循环
        2. 关闭 listenKey
        3. 断开数据流连接
        """
        if not self._user_stream_subscribed:
            return

        # 1. 停止续期循环
        if self._listen_key_renew_task:
            self._listen_key_renew_task.cancel()
            try:
                await self._listen_key_renew_task
            except asyncio.CancelledError:
                pass
            self._listen_key_renew_task = None

        # 2. 关闭 listenKey
        await self._stop_listen_key()

        # 3. 断开数据流连接
        await self._stop_user_stream()

        self._user_stream_subscribed = False
        logger.info(f"[{self.CLIENT_ID}] 用户数据流取消订阅完成")

    # ========== 内部用户数据流管理方法 ==========

    async def _start_user_stream(self, listen_key: str) -> bool:
        """建立用户数据流 WebSocket 连接

        Args:
            listen_key: listenKey

        Returns:
            是否成功建立连接
        """
        logger.info(f"[{self.CLIENT_ID}] 建立用户数据流连接: {listen_key[:10]}...")

        if self._user_stream_running:
            logger.warning(f"[{self.CLIENT_ID}] 用户数据流已在运行")
            return True

        self._user_stream_running = True

        try:
            # 建立 WebSocket 连接
            ws_url = f"{self.USER_STREAM_WS_URI}/{listen_key}"
            connect_kwargs: dict[str, Any] = {}
            if self._proxy_url:
                connect_kwargs["proxy"] = self._proxy_url

            self._user_stream_websocket = await connect(ws_url, **connect_kwargs)
            self._user_stream_connected = True
            logger.info(f"[{self.CLIENT_ID}] 用户数据流 WebSocket 连接成功")

            # 启动接收循环
            self._user_stream_receive_task = asyncio.create_task(self._user_stream_receive_loop())
            return True

        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 用户数据流连接失败: {e}")
            self._user_stream_connected = False
            self._user_stream_running = False
            return False

    async def _stop_user_stream(self) -> None:
        """停止用户数据流连接"""
        if not self._user_stream_running and not self._user_stream_connected:
            return

        self._user_stream_running = False
        self._user_stream_connected = False

        # 取消接收任务
        if self._user_stream_receive_task:
            self._user_stream_receive_task.cancel()
            try:
                await self._user_stream_receive_task
            except asyncio.CancelledError:
                pass
            self._user_stream_receive_task = None

        # 关闭 WebSocket
        if self._user_stream_websocket:
            try:
                await self._user_stream_websocket.close()
            except Exception as e:
                logger.warning(f"[{self.CLIENT_ID}] 关闭 WebSocket 出错: {e}")
            self._user_stream_websocket = None

    async def _user_stream_receive_loop(self) -> None:
        """用户数据流接收循环

        注意：用户数据流断开时不调用回调，只标记状态。
        重连逻辑通过 _reconnect_callback 触发 full_sync() 重新订阅。
        """
        logger.info(f"[{self.CLIENT_ID}] 用户数据流接收循环启动")

        try:
            async for message in self._user_stream_websocket:
                if not self._user_stream_running:
                    break

                try:
                    data = json.loads(message)
                    await self._handle_user_stream_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"[{self.CLIENT_ID}] 用户数据流：无效 JSON 消息")
                except Exception as e:
                    logger.error(f"[{self.CLIENT_ID}] 用户数据流处理消息出错: {e}")

        except asyncio.CancelledError:
            logger.info(f"[{self.CLIENT_ID}] 用户数据流接收循环已取消")
        except ConnectionClosed:
            logger.warning(f"[{self.CLIENT_ID}] 用户数据流连接已关闭")
        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 用户数据流接收循环异常: {e}")
        finally:
            self._user_stream_connected = False
            # 不在这里调用回调，由 _reconnect_callback 触发 full_sync() 处理

    async def _handle_user_stream_message(self, message: dict) -> None:
        """处理用户数据流消息

        职责分离：
        - listenKeyExpired：在客户端内部处理，触发重连
        - 其他所有事件：转发给 BinanceService 处理（通过 _data_callback）

        Args:
            message: 消息数据
        """
        event_type = message.get("e", "unknown")
        logger.debug(f"[{self.CLIENT_ID}] 用户数据流收到事件: {event_type}")

        # listenKeyExpired 是内部管理事件，不转发给 BinanceService
        if event_type == "listenKeyExpired":
            logger.warning(f"[{self.CLIENT_ID}] listenKey 已过期，需要重新订阅")
            if self._reconnect_callback:
                await self._reconnect_callback()
            else:
                logger.warning(f"[{self.CLIENT_ID}] 重连回调未设置，无法自动重连")
            return

        # 其他所有事件都转发给 BinanceService 处理
        package = WSDataPackage(
            client_id=self.CLIENT_ID,
            data=message,
            timestamp=int(time.time() * 1000),
        )

        if self._data_callback:
            await self._data_callback(package)
        else:
            logger.warning(f"[{self.CLIENT_ID}] 数据回调未设置，事件被忽略: {event_type}")

    # ========== API 连接消息处理 ==========
    # 注意：
    # - API 连接（/ws-api/v3）消息由基类 _receive_loop → _handle_message 处理
    # - 用户数据流消息由 _user_stream_receive_loop → _handle_user_stream_message 处理
    # - 两者职责分离：API 连接处理 session.logon 和请求响应，用户数据流处理账户事件

    async def _handle_message(self, message: dict) -> None:
        """处理 API 连接消息（session.logon、请求响应）

        注意：账户事件（ORDER_TRADE_UPDATE, ACCOUNT_UPDATE, listenKeyExpired）
        不从这里处理，它们只从用户数据流连接推送，由 _handle_user_stream_message 处理。

        Args:
            message: 消息数据
        """
        logger.debug(f"[{self.CLIENT_ID}] API连接收到消息: {json.dumps(message)[:500]}")

        # 1. 识别 session.logon 成功响应
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

            # 检查是否是 listenKey 创建响应
            result = message.get("result")
            if isinstance(result, dict) and "listenKey" in result:
                self._listen_key = result["listenKey"]
                logger.debug(f"[{self.CLIENT_ID}] listenKey 已收到: {self._listen_key[:10]}...")
                if self._listen_key_event and not self._listen_key_event.is_set():
                    self._listen_key_event.set()
                return

            # 检查是否是 listenKey 管理响应（ping/stop），这些响应由 WS 客户端自己处理
            if self._pending_listen_key_request_id is not None and request_id == self._pending_listen_key_request_id:
                logger.debug(f"[{self.CLIENT_ID}] listenKey 管理响应已收到并忽略: id={request_id}")
                self._pending_listen_key_request_id = None
                return

            # 使用回调模式处理响应
            if self._response_callback:
                await self._response_callback(request_id, message)
                logger.debug(f"[{self.CLIENT_ID}] 响应已通过回调处理: id={request_id}")
            else:
                logger.debug(f"[{self.CLIENT_ID}] 收到未知请求的响应: id={request_id}")
            return

        # 4. 其他未知消息（账户事件不从 API 连接推送，忽略即可）
        logger.debug(f"[{self.CLIENT_ID}] 收到其他消息: {message.get('e', 'unknown')}")

    # _reconnect 和 _try_reconnect 使用基类实现，无需覆盖
    # 基类使用 self.WS_URI，子类已在 __init__ 中设置了正确的 URI
