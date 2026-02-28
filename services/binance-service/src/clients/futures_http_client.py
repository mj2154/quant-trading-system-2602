"""
币安期货HTTP客户端

继承BinanceHTTPClient基类，配置期货交易API端点。
"""

from typing import Optional, Union

import asyncio

from .base_http_client import BinanceHTTPClient


class BinanceFuturesHTTPClient(BinanceHTTPClient):
    """币安期货HTTP客户端"""

    BASE_URL = "https://fapi.binance.com"
    API_VERSION = "fapi/v1"

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500,
    ) -> list[list]:
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1000),
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        return await self._get("fapi/v1/klines", params)

    async def get_24hr_ticker(
        self,
        symbol: Optional[str] = None,
        symbols: Optional[list[str]] = None,
    ) -> Union[dict, list]:
        """获取24小时ticker数据

        期货API不支持批量查询，使用asyncio.gather并发查询。

        Args:
            symbol: 单个交易对（可选）
            symbols: 交易对列表（可选）

        Returns:
            ticker数据（单个对象或数组）
        """
        if symbols:
            # 期货不支持批量查询，使用并发查询
            tasks = [self.get_24hr_ticker(symbol=s) for s in symbols if s]
            return await asyncio.gather(*tasks)
        elif symbol:
            params = {"symbol": symbol.upper()}
            return await self._get("fapi/v1/ticker/24hr", params)
        else:
            raise ValueError("必须提供 symbol 或 symbols 参数")

    async def get_exchange_info(self) -> dict:
        return await self._get("fapi/v1/exchangeInfo")

    async def get_continuous_klines(
        self,
        pair: str,
        contract_type: str = "PERPETUAL",
        interval: str = "1m",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500,
    ) -> list[list]:
        params = {
            "pair": pair.upper(),
            "contractType": contract_type,
            "interval": interval,
            "limit": min(limit, 1000),
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        return await self._get("fapi/v1/continuousKlines", params)
