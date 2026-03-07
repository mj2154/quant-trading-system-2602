"""
现货私有WebSocket客户端

支持Ed25519签名认证的现货私有WebSocket API客户端。
用于执行订单操作：下单、撤单、查询订单。

WebSocket端点：wss://demo-ws-api.binance.com/ws-api/v3 (仅Demo模式)

关键特性（设计文档 8.10.10）：
1. 请求级签名认证 - 每个请求都带 apiKey + timestamp + signature
2. 签名payload按键名字母顺序排序（与REST API不同）
3. 请求/响应通过ID关联
4. 重连逻辑与公共WS客户端一致（无需重新认证）
"""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Optional

from websockets.asyncio.client import connect

from clients.base_ws_client import BaseWSClient
from models.ws_trading_models import WSResponse
from utils.ed25519_signer import Ed25519Signer

logger = logging.getLogger(__name__)


class BinanceSpotPrivateWSClient(BaseWSClient):
    """现货私有WebSocket客户端

    支持Ed25519签名认证的现货私有WebSocket API。

    特点（设计文档 8.10.10 请求级签名）：
    - 每个请求都带 apiKey + timestamp + signature（无需session.logon认证）
    - 签名payload按字母顺序排序
    - 支持order.place、order.cancel、order.status请求
    - 使用回调模式处理响应
    - 重连逻辑与公共WS客户端一致

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
        """初始化私有WebSocket客户端

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

    def set_response_callback(
        self, callback: Callable[[str, dict], Awaitable[None]]
    ) -> None:
        """设置响应回调

        Args:
            callback: 回调函数，签名为 (request_id: str, response: dict) -> Awaitable[None]
        """
        self._response_callback = callback
        logger.debug(f"[{self.CLIENT_ID}] 响应回调已设置")

    async def send_request(self, method: str, params: dict, request_id: str) -> None:
        """发送请求（不等待响应，通过回调处理响应）

        设计文档 8.10.10：每个请求都带签名认证，无需连接级认证

        Args:
            method: WebSocket API方法名
            params: 请求参数（已包含签名）
            request_id: 请求ID，用于关联响应
        """
        request = {
            "id": request_id,
            "method": method,
            "params": params,
        }

        await self._send(request)
        logger.debug(f"[{self.CLIENT_ID}] 请求已发送: method={method}, id={request_id}")

    async def connect(self) -> None:
        """建立WebSocket连接

        设计文档 8.10.10：无需连接级认证，每个请求都带签名
        """
        if self._state.connected:
            return

        logger.info(f"[{self.CLIENT_ID}] 正在连接...")
        try:
            connect_kwargs: dict[str, Any] = {}
            if self._proxy_url:
                connect_kwargs["proxy"] = self._proxy_url

            self._websocket = await connect(self.WS_URI, **connect_kwargs)
            self._state.connected = True
            self._running = True
            logger.info(f"[{self.CLIENT_ID}] 已连接")

            # 启动接收循环
            self._receive_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 连接失败: {e}")
            self._state.connected = False
            self._running = True
            # 调度持续重连
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
            self._reconnect_task = asyncio.create_task(self._schedule_reconnect())

    def _create_ws_payload(self, params: dict) -> str:
        """创建WebSocket签名的payload"""
        sorted_params = dict(sorted(params.items()))
        return "&".join(f"{k}={v}" for k, v in sorted_params.items())

    def _build_order_params(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        time_in_force: Optional[str] = None,
        stop_price: Optional[float] = None,
        quote_order_qty: Optional[float] = None,
        iceberg_qty: Optional[float] = None,
        new_client_order_id: Optional[str] = None,
        recv_window: Optional[int] = None,
    ) -> dict[str, Any]:
        """构建订单参数"""
        timestamp = int(time.time() * 1000)

        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
            "timestamp": timestamp,
            "apiKey": self.api_key,  # 现货订单需要apiKey
        }

        if price is not None:
            params["price"] = str(price)

        if time_in_force is not None:
            params["timeInForce"] = time_in_force.upper()

        if stop_price is not None:
            params["stopPrice"] = str(stop_price)

        if quote_order_qty is not None:
            params["quoteOrderQty"] = str(quote_order_qty)

        if iceberg_qty is not None:
            params["icebergQty"] = str(iceberg_qty)

        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id

        if recv_window is not None:
            params["recvWindow"] = recv_window

        # 生成签名
        payload = self._create_ws_payload(params)
        params["signature"] = self._signer.sign(payload)

        return params

    def _build_cancel_order_params(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        orig_client_order_id: Optional[str] = None,
        recv_window: Optional[int] = None,
    ) -> dict[str, Any]:
        """构建撤单参数"""
        timestamp = int(time.time() * 1000)

        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "timestamp": timestamp,
            "apiKey": self.api_key,  # 现货订单需要apiKey
        }

        if order_id is not None:
            params["orderId"] = order_id

        if orig_client_order_id is not None:
            params["origClientOrderId"] = orig_client_order_id

        if recv_window is not None:
            params["recvWindow"] = recv_window

        payload = self._create_ws_payload(params)
        params["signature"] = self._signer.sign(payload)

        return params

    def _build_query_order_params(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        orig_client_order_id: Optional[str] = None,
        recv_window: Optional[int] = None,
    ) -> dict[str, Any]:
        """构建查询订单参数"""
        timestamp = int(time.time() * 1000)

        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "timestamp": timestamp,
            "apiKey": self.api_key,  # 现货订单需要apiKey
        }

        if order_id is not None:
            params["orderId"] = order_id

        if orig_client_order_id is not None:
            params["origClientOrderId"] = orig_client_order_id

        if recv_window is not None:
            params["recvWindow"] = recv_window

        payload = self._create_ws_payload(params)
        params["signature"] = self._signer.sign(payload)

        return params

    def _parse_response(self, response_data: dict) -> WSResponse:
        """解析WebSocket响应"""
        return WSResponse.model_validate(response_data)

    async def _handle_message(self, message: dict) -> None:
        """处理接收收到的消息

        设计文档 8.10.10：无需连接级认证，直接处理响应
        """
        # 识别响应消息（包含id和result/status）
        if "id" in message and ("result" in message or "status" in message):
            request_id = str(message["id"])

            # 使用回调模式处理响应（设计文档 8.10.10：每个请求都带签名，无需认证回调）
            if self._response_callback:
                await self._response_callback(request_id, message)
                logger.debug(f"[{self.CLIENT_ID}] 响应已通过回调处理: id={request_id}")
            else:
                logger.debug(f"[{self.CLIENT_ID}] 收到未知请求的响应: id={request_id}")
            return

        logger.debug(f"[{self.CLIENT_ID}] 收到其他消息: {message.get('e', 'unknown')}")

    async def _reconnect(self) -> None:
        """断线重连

        设计文档 8.10.10：重连逻辑与公共WS客户端一致，无需重新认证
        """
        if not self._running:
            return

        logger.info(f"[{self.CLIENT_ID}] 尝试重新连接...")

        # 1. 正确关闭旧连接
        old_websocket = self._websocket
        self._websocket = None
        self._state.connected = False

        if old_websocket:
            try:
                await old_websocket.close()
                logger.debug(f"[{self.CLIENT_ID}] 旧连接已关闭")
            except Exception as e:
                logger.warning(f"[{self.CLIENT_ID}] 关闭旧连接时出错: {e}")

        # 2. 尝试创建新连接
        success = await self._try_reconnect()

        if not success and self._running:
            # 调度持续重试任务
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
            self._reconnect_task = asyncio.create_task(self._schedule_reconnect())

    async def _try_reconnect(self) -> bool:
        """尝试重连，返回是否成功

        设计文档 8.10.10：重连逻辑与公共WS客户端一致，无需重新认证
        """
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
            connect_kwargs = {}
            if self._proxy_url:
                connect_kwargs["proxy"] = self._proxy_url

            self._websocket = await connect(self.WS_URI, **connect_kwargs)
            self._state.connected = True
            logger.info(f"[{self.CLIENT_ID}] 已重新连接")

            # 设计文档 8.10.10：无需重新认证，每个请求都带签名

            if self._reconnect_callback:
                await self._reconnect_callback()

            self._receive_task = asyncio.create_task(self._receive_loop())
            self._reconnect_task = None
            return True

        except Exception as e:
            logger.error(f"[{self.CLIENT_ID}] 重连失败: {e}")
            self._state.connected = False
            return False
