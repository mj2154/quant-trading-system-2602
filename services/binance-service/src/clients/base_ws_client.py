"""
WebSocket客户端基类

设计原则：
- WS客户端只负责连接和接收数据
- 收到数据后立即打包为 WSDataPackage，发送给币安服务
- 不维护任何回调或订阅状态
- 所有数据处理由币安服务统一完成
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Awaitable, Optional

from websockets.asyncio.client import connect, ClientConnection
from websockets.exceptions import ConnectionClosed

from models.ws_message import WSSubscribeRequest, WSUnsubscribeRequest

logger = logging.getLogger(__name__)


@dataclass
class WSDataPackage:
    """WS客户端数据包

    字段说明：
    - client_id: 客户端唯一标识，如 "binance-spot-ws-001"
    - data: 原始数据（币安WS返回什么就返回什么）
    - timestamp: 时间戳（毫秒）
    """

    client_id: str
    data: dict
    timestamp: int


class WSConnectionState:
    """WebSocket连接状态"""

    connected: bool = False
    reconnecting: bool = False  # 防止并发重连


class BaseWSClient:
    """WebSocket客户端基类

    子类必须设置：
    - WS_URI: WebSocket端点URL
    - CLIENT_ID: 唯一客户端标识
    """

    WS_URI: str = ""
    CLIENT_ID: str = ""

    def __init__(self, proxy_url: Optional[str] = None) -> None:
        self._state = WSConnectionState()
        self._running: bool = False
        self._proxy_url = proxy_url
        self._reconnect_callback: Optional[Callable[..., Awaitable[None]]] = None
        self._data_callback: Optional[Callable[[WSDataPackage], Awaitable[None]]] = None
        self._websocket = None
        self._receive_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None  # 重连任务引用，防止被GC
        self._reconnect_lock: asyncio.Lock = asyncio.Lock()  # 重连锁，防止并发重连

    @property
    def client_id(self) -> str:
        return self.CLIENT_ID

    @property
    def is_connected(self) -> bool:
        return self._state.connected

    def set_reconnect_callback(self, callback: Callable[..., Awaitable[None]]) -> None:
        """设置断线重连回调"""
        self._reconnect_callback = callback

    def set_data_callback(
        self, callback: Callable[[WSDataPackage], Awaitable[None]]
    ) -> None:
        """设置数据回调（币安服务接收数据用）"""
        self._data_callback = callback

    async def connect(self) -> None:
        """建立WebSocket连接"""
        if self._state.connected:
            return

        # 调用connect()意味着客户端想要运行，设置_running=True
        self._running = True

        logger.info(f"[{self.CLIENT_ID}] 正在连接...")
        try:
            connect_kwargs: dict[str, Any] = {}
            if self._proxy_url:
                connect_kwargs["proxy"] = self._proxy_url

            self._websocket = await connect(
                self.WS_URI,
                open_timeout=3.0,
                close_timeout=5.0,
                **connect_kwargs,
            )

            # 再次检查运行状态（防止在连接过程中被断开）
            if not self._running:
                logger.info(f"[{self.CLIENT_ID}] 连接完成但已停止，关闭连接")
                if self._websocket:
                    await self._websocket.close()
                self._websocket = None
                return

            self._state.connected = True
            logger.info(f"[{self.CLIENT_ID}] 已连接")

            self._receive_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 连接失败: {e}")
            self._state.connected = False
            self._running = True  # 设置为 True 以便重连任务能执行
            # 调度持续重连
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
            self._reconnect_task = asyncio.create_task(self._schedule_reconnect())

    async def disconnect(self) -> None:
        """断开WebSocket连接"""
        self._running = False

        # 取消重连任务
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.warning(f"[{self.CLIENT_ID}] 关闭连接时出错: {e}")
            self._websocket = None

        self._state.connected = False
        logger.info(f"[{self.CLIENT_ID}] 已断开连接")

    async def subscribe(self, request: WSSubscribeRequest) -> None:
        """订阅流

        Args:
            request: 订阅请求模型
        """
        if not self._state.connected:
            await self.connect()

        await self._send(request.model_dump(by_alias=True))

        logger.info(f"[{self.CLIENT_ID}] 订阅: {request.params}")

    async def unsubscribe(self, request: WSUnsubscribeRequest) -> None:
        """取消订阅流

        Args:
            request: 取消订阅请求模型
        """
        await self._send(request.model_dump(by_alias=True))

        logger.info(f"[{self.CLIENT_ID}] 取消订阅: {request.params}")

    async def _receive_loop(self) -> None:
        """接收数据循环"""
        logger.info(f"[{self.CLIENT_ID}] 接收循环启动")
        reconnect_needed = False

        # 防御性检查：确保 WebSocket 已创建
        if not self._websocket:
            logger.warning(f"[{self.CLIENT_ID}] WebSocket 为 None，跳过接收循环")
            if self._running:
                await self._reconnect()
            return

        try:
            async for message in self._websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"[{self.CLIENT_ID}] 无效的JSON消息")
                except Exception as e:
                    logger.error(f"[{self.CLIENT_ID}] 处理WebSocket消息时出错: {e}")

        except asyncio.CancelledError:
            logger.info(f"[{self.CLIENT_ID}] 接收循环已取消")
        except ConnectionClosed:
            logger.warning(f"[{self.CLIENT_ID}] 连接已关闭，标记需要重连...")
            self._state.connected = False
            reconnect_needed = True
        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 接收循环异常: {e}")
        finally:
            self._state.connected = False
            if reconnect_needed and self._running:
                # 尝试重连，失败则调度持续重试
                await self._reconnect()

    async def _reconnect(self) -> None:
        """断线重连

        确保旧连接完全关闭后再创建新连接，避免 websockets 库状态损坏。
        重连失败后调度持续重试任务。
        """
        if not self._running:
            return

        logger.info(f"[{self.CLIENT_ID}] 尝试重新连接...")

        # 1. 正确关闭旧连接
        old_websocket = self._websocket
        self._websocket = None
        self._state.connected = False

        await self._close_websocket(old_websocket)

        # 2. 尝试创建新连接
        success = await self._try_reconnect()

        if not success and self._running:
            # 调度持续重试任务
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
            self._reconnect_task = asyncio.create_task(self._schedule_reconnect())

    async def _schedule_reconnect(self) -> None:
        """调度延迟重连（持续重试直到成功）"""
        try:
            while self._running and not self._state.connected:
                logger.info(f"[{self.CLIENT_ID}] 等待 2 秒后重试...")
                await asyncio.sleep(2)
                if not self._running:
                    break
                if await self._try_reconnect():  # 成功返回 True
                    break
            logger.info(f"[{self.CLIENT_ID}] 重连任务完成（已连接或已停止）")
        except asyncio.CancelledError:
            logger.info(f"[{self.CLIENT_ID}] 重连任务已取消")

    async def _try_reconnect(self) -> bool:
        """尝试重连，返回是否成功

        使用重连锁防止并发调用。
        """
        async with self._reconnect_lock:
            # 再次检查连接状态（锁内检查，防止在等待锁期间被其他任务连接成功）
            if self._state.connected:
                logger.debug(f"[{self.CLIENT_ID}] 已有连接，无需重连")
                return True

            try:
                # 关闭旧连接（如果存在）
                await self._close_websocket(self._websocket)
                self._websocket = None
                self._state.connected = False

                # 创建新连接
                connect_kwargs: dict[str, Any] = {}
                if self._proxy_url:
                    connect_kwargs["proxy"] = self._proxy_url

                self._websocket = await connect(
                    self.WS_URI,
                    open_timeout=3.0,
                    close_timeout=5.0,
                    **connect_kwargs,
                )
                self._state.connected = True
                logger.info(f"[{self.CLIENT_ID}] 已重新连接")

                if self._reconnect_callback:
                    await self._reconnect_callback()

                self._receive_task = asyncio.create_task(self._receive_loop())
                self._reconnect_task = None  # 重连成功，清除任务引用
                return True

            except Exception as e:
                logger.error(f"[{self.CLIENT_ID}] 重连失败: {e}")
                self._state.connected = False
                return False

    async def _handle_message(self, message: dict) -> None:
        """处理接收到的消息

        收到数据后立即打包发送给币安服务，不做任何处理
        """
        # 识别币安ACK确认消息 {"result": null, "id": xxx}
        if "result" in message and "id" in message:
            logger.debug(
                f"[{self.CLIENT_ID}] 收到ACK确认: result={message.get('result')}, id={message['id']}"
            )
            return

        # 打包数据
        package = WSDataPackage(
            client_id=self.CLIENT_ID,
            data=message,
            timestamp=int(time.time() * 1000),
        )

        # 发送给币安服务
        if self._data_callback:
            await self._data_callback(package)

    async def _close_websocket(self, websocket: Optional[ClientConnection]) -> None:
        """安全关闭 WebSocket 连接"""
        if websocket:
            try:
                await websocket.close()
                logger.debug(f"[{self.CLIENT_ID}] 旧连接已关闭")
            except Exception as e:
                logger.warning(f"[{self.CLIENT_ID}] 关闭旧连接时出错: {e}")

    async def _send(self, message: dict) -> None:
        """发送消息"""
        if self._websocket and self._state.connected:
            try:
                await self._websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"[{self.CLIENT_ID}] 发送消息失败: {e}")
