"""
币安现货私有数据HTTP客户端

支持Ed25519和RSA签名认证的现货私有API调用功能。

现货API文档: https://binance-docs.github.io/apidocs/spot/cn/
"""

import time
from typing import Optional
from urllib.parse import urlencode

from .base_http_client import BinanceHTTPClient
from models.spot_account import SpotAccountInfo
from utils.ed25519_signer import Ed25519Signer
from utils.rsa_signer import RSASigner


class BinanceSpotPrivateHTTPClient(BinanceHTTPClient):
    """币安现货私有数据HTTP客户端

    支持Ed25519和RSA签名认证的现货私有API调用。

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

    BASE_URL = "https://demo-api.binance.com"

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
    ) -> SpotAccountInfo:
        """获取账户信息

        调用 GET /api/v3/account 获取账户详情。

        Args:
            recv_window: 接收窗口时间（毫秒），默认5000

        Returns:
            账户信息模型
        """
        response = await self._signed_request(
            method="GET",
            path="api/v3/account",
            params={},
            recv_window=recv_window or 5000,
        )

        return SpotAccountInfo.model_validate(response)

    async def get_order(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        orig_client_order_id: Optional[str] = None,
        recv_window: Optional[int] = None,
    ) -> dict:
        """获取订单信息

        调用 GET /api/v3/order 获取订单详情。

        Args:
            symbol: 交易对符号
            order_id: 订单ID
            orig_client_order_id: 客户端订单ID
            recv_window: 接收窗口时间

        Returns:
            订单信息
        """
        params = {"symbol": symbol.upper()}

        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id

        return await self._signed_request(
            method="GET",
            path="api/v3/order",
            params=params,
            recv_window=recv_window,
        )

    async def get_open_orders(
        self,
        symbol: Optional[str] = None,
        recv_window: Optional[int] = None,
    ) -> list[dict]:
        """获取当前挂单

        调用 GET /api/v3/openOrders 获取当前所有挂单。

        Args:
            symbol: 交易对符号（可选）
            recv_window: 接收窗口时间

        Returns:
            挂单列表
        """
        params: dict = {}
        if symbol:
            params["symbol"] = symbol.upper()

        return await self._signed_request(
            method="GET",
            path="api/v3/openOrders",
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
        """获取所有订单

        调用 GET /api/v3/allOrders 获取历史订单。

        Args:
            symbol: 交易对符号
            start_time: 开始时间戳
            end_time: 结束时间戳
            limit: 返回数量限制
            recv_window: 接收窗口时间

        Returns:
            订单列表
        """
        params = {"symbol": symbol.upper()}

        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        if limit is not None:
            params["limit"] = limit

        return await self._signed_request(
            method="GET",
            path="api/v3/allOrders",
            params=params,
            recv_window=recv_window,
        )
