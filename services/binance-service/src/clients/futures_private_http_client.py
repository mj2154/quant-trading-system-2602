"""
币安期货私有数据HTTP客户端

支持Ed25519和RSA签名认证的期货私有API调用功能。

期货API文档: https://binance-docs.github.io/apidocs/futures/cn/
"""

import time
from typing import Optional
from urllib.parse import urlencode

from .base_http_client import BinanceHTTPClient
from models.futures_account import FuturesAccountInfo
from models.trading_order import (
    OrderSide,
    OrderType,
    OrderResponseType,
    PositionSide,
    TimeInForce,
    FuturesOrderRequest,
)
from utils.ed25519_signer import Ed25519Signer
from utils.rsa_signer import RSASigner


class BinanceFuturesPrivateHTTPClient(BinanceHTTPClient):
    """币安期货私有数据HTTP客户端

    支持Ed25519和RSA签名认证的期货私有API调用。

    签名流程：
    1. 构建query string参数
    2. 添加timestamp和recvWindow
    3. 创建payload (按key排序的query string)
    4. 使用私钥签名
    5. 将签名作为signature参数传递（需URL编码）
    6. 在header中传递X-MBX-APIKEY

    Args:
        api_key: 币安API Key
        private_key_pem: Ed25519或RSA私钥（PEM格式）
        signature_type: 签名类型，"ed25519" 或 "rsa"，默认"ed25519"
        timeout: 请求超时时间（秒）
        proxy_url: 可选的代理URL
    """

    BASE_URL = "https://demo-fapi.binance.com"

    # 支持的签名类型
    VALID_SIGNATURE_TYPES = {"ed25519", "rsa"}

    def __init__(
        self,
        api_key: str,
        private_key_pem: bytes,
        signature_type: str = "ed25519",
        timeout: float = 10.0,
        proxy_url: Optional[str] = None,
    ) -> None:
        """初始化私有客户端

        Args:
            api_key: 币安API Key
            private_key_pem: Ed25519或RSA私钥PEM格式
            signature_type: 签名类型，"ed25519" 或 "rsa"
            timeout: 请求超时时间
            proxy_url: 可选的代理URL

        Raises:
            ValueError: 如果签名类型无效
        """
        super().__init__(timeout=timeout, proxy_url=proxy_url)
        self.api_key = api_key

        # 验证签名类型
        signature_type_lower = signature_type.lower()
        if signature_type_lower not in self.VALID_SIGNATURE_TYPES:
            raise ValueError(
                f"Invalid signature type: {signature_type}. "
                f"Must be one of {self.VALID_SIGNATURE_TYPES}"
            )

        # 根据签名类型选择签名器
        if signature_type_lower == "rsa":
            self._signer = RSASigner(private_key_pem)
        else:
            self._signer = Ed25519Signer(private_key_pem)

        self._signature_type = signature_type_lower

    def _generate_timestamp(self) -> str:
        """生成毫秒级时间戳

        Returns:
            13位毫秒时间戳字符串
        """
        return str(int(time.time() * 1000))

    def _create_payload(self, params: dict) -> str:
        """创建签名的payload

        按参数添加顺序构建query string（与官方示例一致）。

        Args:
            params: 参数字典

        Returns:
            URL编码后的query string
        """
        # 按原始顺序（不排序），与官方示例一致
        return urlencode(params, encoding="UTF-8")

    def _build_signed_params(
        self, params: Optional[dict] = None, recv_window: Optional[int] = None
    ) -> dict:
        """构建带签名的参数

        Args:
            params: 原始参数
            recv_window: 接收窗口时间（毫秒）

        Returns:
            包含签名和timestamp的参数字典
        """
        # 初始化参数
        request_params = dict(params) if params else {}

        # 添加timestamp
        request_params["timestamp"] = self._generate_timestamp()

        # 添加recvWindow（可选）
        if recv_window is not None:
            request_params["recvWindow"] = str(recv_window)

        # 创建payload
        payload = self._create_payload(request_params)

        # 生成签名
        signature = self._signer.sign(payload)

        # 添加签名（不进行URL编码，httpx会自动处理）
        request_params["signature"] = signature

        return request_params

    async def _signed_request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        recv_window: Optional[int] = None,
    ) -> dict:
        """发送签名请求

        Args:
            method: HTTP方法
            path: API路径
            params: 请求参数
            recv_window: 接收窗口时间

        Returns:
            JSON响应数据
        """
        # 构建带签名的参数
        signed_params = self._build_signed_params(params, recv_window)

        url = f"{self.BASE_URL}/{path}"

        headers = {
            "X-MBX-APIKEY": self.api_key,
        }

        # GET请求用params，POST请求用data
        if method == "GET":
            response = await self._client.request(
                method=method,
                url=url,
                params=signed_params,
                headers=headers,
            )
        else:
            response = await self._client.request(
                method=method,
                url=url,
                data=signed_params,
                headers=headers,
            )
        response.raise_for_status()
        return response.json()

    async def get_account_info(
        self, recv_window: Optional[int] = None
    ) -> FuturesAccountInfo:
        """获取期货账户信息

        调用 GET /fapi/v3/account 获取账户详情。
        注意：此接口仅返回有持仓或挂单的交易对。

        Args:
            recv_window: 接收窗口时间（毫秒），默认5000

        Returns:
            期货账户信息模型
        """
        response = await self._signed_request(
            method="GET",
            path="fapi/v3/account",
            params={},
            recv_window=recv_window or 5000,
        )

        return FuturesAccountInfo.model_validate(response)

    async def get_balance(self, recv_window: Optional[int] = None) -> list[dict]:
        """获取期货账户余额

        调用 GET /fapi/v3/balance 获取账户余额详情。

        Args:
            recv_window: 接收窗口时间（毫秒），默认5000

        Returns:
            余额列表
        """
        return await self._signed_request(
            method="GET",
            path="fapi/v3/balance",
            params={},
            recv_window=recv_window or 5000,
        )

    async def get_position_risk(self, recv_window: Optional[int] = None) -> list[dict]:
        """获取持仓风险

        调用 GET /fapi/v3/positionRisk 获取持仓风险信息。

        Args:
            recv_window: 接收窗口时间（毫秒），默认5000

        Returns:
            持仓风险列表
        """
        return await self._signed_request(
            method="GET",
            path="fapi/v3/positionRisk",
            params={},
            recv_window=recv_window or 5000,
        )

    # ========== 交易相关方法 ==========

    async def create_order(
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
        new_order_resp_type: str = "ACK",
        recv_window: Optional[int] = None,
    ) -> dict:
        """创建新订单

        调用 POST /fapi/v1/order 创建新订单。

        Args:
            symbol: 交易对，如 BTCUSDT
            side: 订单方向，BUY 或 SELL
            order_type: 订单类型，LIMIT, MARKET, STOP, TAKE_PROFIT 等
            quantity: 订单数量
            price: 价格（限价单必需）
            time_in_force: 时间策略，GTC, IOC, FOK, GTD
            stop_price: 止损/止盈价格
            reduce_only: 是否仅减仓
            position_side: 持仓方向，LONG, SHORT, BOTH（对冲模式）
            new_client_order_id: 客户端订单ID
            new_order_resp_type: 响应类型，ACK, RESULT
            recv_window: 接收窗口时间

        Returns:
            订单响应
        """
        params: dict = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
            "newOrderRespType": new_order_resp_type.upper(),
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

        return await self._signed_request(
            method="POST",
            path="fapi/v1/order",
            params=params,
            recv_window=recv_window,
        )

    async def test_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        time_in_force: Optional[str] = None,
        stop_price: Optional[float] = None,
        recv_window: Optional[int] = None,
    ) -> dict:
        """测试下单（不执行）

        调用 POST /fapi/v1/order/test 测试下单参数。

        Args:
            symbol: 交易对
            side: 订单方向
            order_type: 订单类型
            quantity: 订单数量
            price: 价格
            time_in_force: 时间策略
            stop_price: 止损价格
            recv_window: 接收窗口时间

        Returns:
            测试结果
        """
        params: dict = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
        }

        if price is not None:
            params["price"] = str(price)

        if time_in_force is not None:
            params["timeInForce"] = time_in_force.upper()

        if stop_price is not None:
            params["stopPrice"] = str(stop_price)

        return await self._signed_request(
            method="POST",
            path="fapi/v1/order/test",
            params=params,
            recv_window=recv_window,
        )

    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        orig_client_order_id: Optional[str] = None,
        recv_window: Optional[int] = None,
    ) -> dict:
        """撤销订单

        调用 DELETE /fapi/v1/order 撤销订单。

        Args:
            symbol: 交易对
            order_id: 订单ID
            orig_client_order_id: 客户端订单ID
            recv_window: 接收窗口时间

        Returns:
            撤销结果
        """
        params: dict = {"symbol": symbol.upper()}

        if order_id is not None:
            params["orderId"] = order_id

        if orig_client_order_id is not None:
            params["origClientOrderId"] = orig_client_order_id

        return await self._signed_request(
            method="DELETE",
            path="fapi/v1/order",
            params=params,
            recv_window=recv_window,
        )

    async def get_order(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        orig_client_order_id: Optional[str] = None,
        recv_window: Optional[int] = None,
    ) -> dict:
        """查询订单

        调用 GET /fapi/v1/order 查询订单详情。

        Args:
            symbol: 交易对
            order_id: 订单ID
            orig_client_order_id: 客户端订单ID
            recv_window: 接收窗口时间

        Returns:
            订单详情
        """
        params: dict = {"symbol": symbol.upper()}

        if order_id is not None:
            params["orderId"] = order_id

        if orig_client_order_id is not None:
            params["origClientOrderId"] = orig_client_order_id

        return await self._signed_request(
            method="GET",
            path="fapi/v1/order",
            params=params,
            recv_window=recv_window,
        )

    async def get_open_orders(
        self,
        symbol: Optional[str] = None,
        recv_window: Optional[int] = None,
    ) -> list[dict]:
        """查询当前挂单

        调用 GET /fapi/v1/openOrders 获取当前所有挂单。

        Args:
            symbol: 交易对（可选）
            recv_window: 接收窗口时间

        Returns:
            挂单列表
        """
        params: dict = {}
        if symbol is not None:
            params["symbol"] = symbol.upper()

        return await self._signed_request(
            method="GET",
            path="fapi/v1/openOrders",
            params=params,
            recv_window=recv_window,
        )

    async def get_all_orders(
        self,
        symbol: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None,
        recv_window: Optional[int] = None,
    ) -> list[dict]:
        """查询所有订单

        调用 GET /fapi/v1/allOrders 获取历史订单。

        Args:
            symbol: 交易对
            start_time: 开始时间戳
            end_time: 结束时间戳
            limit: 返回数量限制
            recv_window: 接收窗口时间

        Returns:
            订单列表
        """
        params: dict = {"symbol": symbol.upper()}

        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        if limit is not None:
            params["limit"] = limit

        return await self._signed_request(
            method="GET",
            path="fapi/v1/allOrders",
            params=params,
            recv_window=recv_window,
        )

    async def set_leverage(
        self,
        symbol: str,
        leverage: int,
        recv_window: Optional[int] = None,
    ) -> dict:
        """设置杠杆倍数

        调用 POST /fapi/v1/leverage 设置杠杆。

        Args:
            symbol: 交易对
            leverage: 杠杆倍数
            recv_window: 接收窗口时间

        Returns:
            设置结果
        """
        params: dict = {
            "symbol": symbol.upper(),
            "leverage": leverage,
        }

        return await self._signed_request(
            method="POST",
            path="fapi/v1/leverage",
            params=params,
            recv_window=recv_window,
        )
