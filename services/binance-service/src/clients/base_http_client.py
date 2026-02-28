"""
币安HTTP客户端基类

提供通用的HTTP请求功能，子类只需配置端点参数。
"""

import httpx
from typing import Optional, Union


class BinanceHTTPClient:
    """币安HTTP客户端基类

    职责：
    - 管理HTTP连接
    - 提供通用的GET请求方法
    - 返回原始数据，由调用方负责转换
    """

    BASE_URL: str = ""
    API_VERSION: str = ""

    def __init__(
        self,
        timeout: float = 10.0,
        proxy_url: Optional[str] = None,
    ) -> None:
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

        if proxy_url:
            transport = httpx.AsyncHTTPTransport(proxy=proxy_url)
        else:
            transport = None

        self._client = httpx.AsyncClient(
            timeout=timeout,
            transport=transport,
            limits=limits,
        )

    async def __aenter__(self) -> "BinanceHTTPClient":
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器退出"""
        await self.close()

    async def close(self) -> None:
        """关闭HTTP客户端"""
        await self._client.aclose()

    async def _get(self, path: str, params: Optional[dict] = None) -> Union[dict, list]:
        """通用GET请求方法

        Args:
            path: API路径（如 "api/v3/klines" 或 "fapi/v1/klines"）
            params: 请求参数

        Returns:
            JSON响应数据（单个对象或数组）
        """
        url = f"{self.BASE_URL}/{path}"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500,
    ) -> list[list]:
        """获取K线数据

        Args:
            symbol: 交易对符号
            interval: K线间隔
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            limit: 返回数量限制

        Returns:
            原始K线数据列表
        """
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1000),
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        return await self._get(f"{self.API_VERSION}/klines", params)

    async def get_24hr_ticker(self, symbol: str) -> dict:
        """获取24hr统计信息

        Args:
            symbol: 交易对符号

        Returns:
            原始ticker数据
        """
        params = {"symbol": symbol.upper()}
        return await self._get(f"{self.API_VERSION}/ticker/24hr", params)

    async def get_exchange_info(self) -> dict:
        """获取交易所信息

        Returns:
            原始交易所信息
        """
        return await self._get(f"{self.API_VERSION}/exchangeInfo")

    async def get_server_time(self) -> int:
        """获取服务器时间

        Returns:
            服务器时间戳（毫秒）
        """
        response = await self._client.get(f"{self.BASE_URL}/api/v3/time")
        response.raise_for_status()
        return response.json()["serverTime"]

    def interval_to_resolution(self, interval: str) -> str:
        """将间隔转换为分辨率

        Args:
            interval: K线间隔（如 1m, 5m, 1h）

        Returns:
            分辨率（如 1, 5, 60）
        """
        if interval.endswith("m"):
            return interval[:-1]
        elif interval.endswith("h"):
            return str(int(interval[:-1]) * 60)
        elif interval.endswith("d"):
            return str(int(interval[:-1]) * 1440)
        return interval
