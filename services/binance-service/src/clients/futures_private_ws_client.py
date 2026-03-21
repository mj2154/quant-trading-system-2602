"""
期货私有WebSocket客户端

支持Ed25519签名认证的期货私有WebSocket API客户端。
用于执行订单操作：下单、撤单、查询订单。

WebSocket端点：wss://testnet.binancefuture.com/ws-fapi/v1 (仅Testnet)

关键特性（设计文档 8.10.10）：
1. 请求级签名认证 - 每个请求都带 apiKey + timestamp + signature
2. 签名payload按键名字母顺序排序（与REST API不同）
3. 请求/响应通过ID关联
4. 重连逻辑与公共WS客户端一致（无需重新认证）
"""

import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional

from clients.base_ws_client import BaseWSClient
from models.ws_message import WSResponse
from utils.ed25519_signer import Ed25519Signer

logger = logging.getLogger(__name__)


class BinanceFuturesPrivateWSClient(BaseWSClient):
    """期货私有WebSocket客户端

    支持Ed25519签名认证的期货私有WebSocket API。

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
        use_testnet: 是否使用测试网（默认False）
    """

    # 期货WebSocket端点 - 仅Testnet，生产网地址暂时禁用
    WS_URI = None  # 生产网已禁用，请勿填写
    TESTNET_WS_URI = "wss://testnet.binancefuture.com/ws-fapi/v1"
    CLIENT_ID = "binance-futures-private-ws-001"

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

    # connect() 使用基类实现，无需覆盖
    # 基类包含 open_timeout、close_timeout 和连接过程中的状态检查

    def _create_ws_payload(self, params: dict) -> str:
        """创建WebSocket签名的payload

        WebSocket签名payload必须按键名字母顺序排序（与REST API不同）。

        Args:
            params: 参数字典

        Returns:
            签名的payload字符串
        """
        # 按键名字母顺序排序
        sorted_params = dict(sorted(params.items()))
        # 拼接成query string格式
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
        reduce_only: bool = False,
        position_side: Optional[str] = None,
        new_client_order_id: Optional[str] = None,
        recv_window: Optional[int] = None,
    ) -> dict[str, Any]:
        """构建订单参数

        设计文档 8.10.10：每个请求都带签名认证

        Args:
            symbol: 交易对
            side: 订单方向（BUY/SELL）
            order_type: 订单类型（LIMIT/MARKET/STOP等）
            quantity: 数量
            price: 价格
            time_in_force: 时间策略（GTC/IOC/FOK）
            stop_price: 止损价格
            reduce_only: 是否仅减仓
            position_side: 持仓方向
            new_client_order_id: 客户端订单ID
            recv_window: 接收窗口

        Returns:
            订单参数字典（包含apiKey和signature）
        """
        timestamp = int(time.time() * 1000)

        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
            "timestamp": timestamp,
        }

        if price is not None:
            params["price"] = str(price)

        if time_in_force is not None:
            params["timeInForce"] = time_in_force.upper()

        if stop_price is not None:
            params["stopPrice"] = str(stop_price)

        if reduce_only:
            params["reduceOnly"] = "true"

        if position_side is not None:
            params["positionSide"] = position_side.upper()

        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id

        if recv_window is not None:
            params["recvWindow"] = recv_window

        # 设计文档 8.10.10：每个请求都带签名认证（apiKey + signature）
        params["apiKey"] = self.api_key

        # 生成签名（payload按键名字母顺序排序）
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
        """构建撤单参数

        设计文档 8.10.10：每个请求都带签名认证

        Args:
            symbol: 交易对
            order_id: 订单ID
            orig_client_order_id: 客户端订单ID
            recv_window: 接收窗口

        Returns:
            撤单参数字典（包含apiKey和signature）
        """
        timestamp = int(time.time() * 1000)

        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "timestamp": timestamp,
        }

        if order_id is not None:
            params["orderId"] = order_id
        elif orig_client_order_id is not None:
            params["origClientOrderId"] = orig_client_order_id

        if recv_window is not None:
            params["recvWindow"] = recv_window

        # 设计文档 8.10.10：每个请求都带签名认证（apiKey + signature）
        params["apiKey"] = self.api_key

        # 生成签名（payload按键名字母顺序排序）
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
        """构建查询订单参数

        设计文档 8.10.10：每个请求都带签名认证

        Args:
            symbol: 交易对
            order_id: 订单ID
            orig_client_order_id: 客户端订单ID
            recv_window: 接收窗口

        Returns:
            查询订单参数字典（包含apiKey和signature）
        """
        timestamp = int(time.time() * 1000)

        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "timestamp": timestamp,
        }

        if order_id is not None:
            params["orderId"] = order_id
        elif orig_client_order_id is not None:
            params["origClientOrderId"] = orig_client_order_id

        if recv_window is not None:
            params["recvWindow"] = recv_window

        # 设计文档 8.10.10：每个请求都带签名认证（apiKey + signature）
        params["apiKey"] = self.api_key

        # 生成签名（payload按键名字母顺序排序）
        payload = self._create_ws_payload(params)
        params["signature"] = self._signer.sign(payload)

        return params

    def _build_modify_order_params(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        timestamp: int,
        order_id: Optional[str] = None,
        orig_client_order_id: Optional[str] = None,
        new_client_order_id: Optional[str] = None,
        position_side: Optional[str] = None,
        price_match: Optional[str] = None,
        recv_window: Optional[int] = None,
    ) -> dict[str, Any]:
        """构建修改订单参数

        期货 order.modify API - 可修改价格和数量，仅支持 LIMIT 订单

        设计文档 8.10.10：每个请求都带签名认证

        Args:
            symbol: 交易对
            side: 订单方向（BUY/SELL）
            quantity: 新订单数量
            price: 新订单价格
            timestamp: 时间戳（毫秒）
            order_id: 订单ID
            orig_client_order_id: 客户端订单ID
            new_client_order_id: 新客户端订单ID
            position_side: 持仓方向
            price_match: 价格匹配模式（与price不能同时使用）
            recv_window: 接收窗口

        Returns:
            修改订单参数字典（包含apiKey和signature）

        Note:
            - priceMatch 与 price 不能同时使用
            - 仅支持 LIMIT 订单修改
            - 单个订单最多修改 10000 次
        """
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "quantity": str(quantity),
            "price": str(price),
            "timestamp": timestamp,
        }

        # ID 优先级：orderId > origClientOrderId
        if order_id is not None:
            params["orderId"] = order_id
        elif orig_client_order_id is not None:
            params["origClientOrderId"] = orig_client_order_id

        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id

        if position_side is not None:
            params["positionSide"] = position_side.upper()

        if price_match is not None:
            params["priceMatch"] = price_match

        if recv_window is not None:
            params["recvWindow"] = recv_window

        # 每个请求都带签名认证（apiKey + signature）
        params["apiKey"] = self.api_key

        # 生成签名（payload按键名字母顺序排序）
        payload = self._create_ws_payload(params)
        params["signature"] = self._signer.sign(payload)

        return params

    def _parse_response(self, response_data: dict) -> WSResponse:
        """解析WebSocket响应

        Args:
            response_data: 响应数据

        Returns:
            WSResponse对象
        """
        return WSResponse.model_validate(response_data)

    async def _handle_message(self, message: dict) -> None:
        """处理接收到的消息

        设计文档 8.10.10：无需连接级认证，直接处理响应

        Args:
            message: 消息数据
        """
        logger.info(f"[{self.CLIENT_ID}] 收到消息: {json.dumps(message)[:500]}")

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

        # 处理其他消息（如用户数据流）- 暂时不实现
        logger.debug(f"[{self.CLIENT_ID}] 收到其他消息: {message.get('e', 'unknown')}")

    # _reconnect 和 _try_reconnect 使用基类实现，无需覆盖
    # 基类使用 self.WS_URI，子类已在 __init__ 中设置了正确的 URI
