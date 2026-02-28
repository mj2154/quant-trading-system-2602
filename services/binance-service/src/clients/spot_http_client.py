"""
币安现货HTTP客户端

继承BinanceHTTPClient基类，配置现货交易API端点。
"""

from typing import Optional

from .base_http_client import BinanceHTTPClient


class BinanceSpotHTTPClient(BinanceHTTPClient):
    """币安现货HTTP客户端"""

    BASE_URL = "https://api.binance.com"
    API_VERSION = "v3"

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
        return await self._get("api/v3/klines", params)

    async def get_24hr_ticker(
        self,
        symbol: Optional[str] = None,
        symbols: Optional[list[str]] = None,
    ) -> Union[dict, list]:
        """获取24小时ticker数据

        支持单个查询或批量查询：
        - 单个查询: symbol="BTCUSDT" -> 返回单个对象
        - 批量查询: symbols=["BTCUSDT","ETHUSDT"] -> 返回数组

        Args:
            symbol: 单个交易对（可选）
            symbols: 交易对列表（可选，最多100个）

        Returns:
            ticker数据（单个对象或数组）
        """
        import json

        if symbols:
            # 批量查询，symbols参数需要URL编码的JSON格式
            # 币安要求格式: ["BTCUSDT","ETHUSDT"]（无空格，双引号）
            symbols_list = [s.upper() for s in symbols if s]
            symbols_json = json.dumps(symbols_list, separators=(",", ":"))
            params = {"symbols": symbols_json}
        elif symbol:
            params = {"symbol": symbol.upper()}
        else:
            raise ValueError("必须提供 symbol 或 symbols 参数")

        return await self._get("api/v3/ticker/24hr", params)

    async def get_exchange_info(self) -> dict:
        return await self._get("api/v3/exchangeInfo")
