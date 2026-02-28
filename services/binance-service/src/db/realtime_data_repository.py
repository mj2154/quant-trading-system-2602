"""
RealtimeData 表仓储

根据 SUBSCRIPTION_AND_REALTIME_DATA.md 设计，用于管理持续订阅的实时数据。
订阅键格式：{EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{RESOLUTION}]

事件驱动流程：
1. API网关 INSERT realtime_data 表 → 触发 subscription.add 通知
2. API网关 DELETE realtime_data 表 → 触发 subscription.remove 通知
3. 币安服务 UPDATE realtime_data.data → 触发 realtime.update 通知
4. API网关监听 realtime.update 通知，推送数据给前端

支持的数据类型：
- KLINE: K线数据，如 "BINANCE:BTCUSDT@KLINE_1m"
- QUOTES: 报价数据，如 "BINANCE:BTCUSDT@QUOTES"
- TRADE: 成交数据，如 "BINANCE:BTCUSDT@TRADE"

参考设计文档：
- Section 2.2: realtime_data 实时数据表
- Section 2.2.1: 通知设计
- Section 2.2.2: 触发器实现
- Section 2.2.3: 数据类型与订阅键映射
"""

import logging
import json
from typing import Any, Optional, List

import asyncpg

from utils import resolution_to_interval

logger = logging.getLogger(__name__)


class RealtimeDataRepository:
    """RealtimeData 表仓储

    职责：
    - 更新实时数据（触发 realtime_update 通知）
    - 获取所有订阅键（断线重连恢复用）
    - 解析订阅键提取信息

    使用方式：
        repo = RealtimeDataRepository(pool)
        await repo.update_data(subscription_key, data)
        await repo.get_all_subscriptions()
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """初始化仓储

        Args:
            pool: asyncpg 连接池
        """
        self._pool = pool

    async def update_data(self, subscription_key: str, data: Any, event_time: Optional[str] = None) -> None:
        """更新实时数据

        触发 realtime_update 通知，通知API网关数据已更新。

        Args:
            subscription_key: 订阅键，如 "BINANCE:BTCUSDT@KLINE_1m"
            data: 实时数据（JSON格式）
            event_time: 事件时间（可选，默认为当前时间）
        """
        import json
        from datetime import datetime

        def json_serializer(obj):
            """自定义JSON序列化器，处理datetime类型"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        query = """
            UPDATE realtime_data
            SET data = $1, event_time = COALESCE($2, NOW()), updated_at = NOW()
            WHERE subscription_key = $3
        """
        async with self._pool.acquire() as conn:
            data_json = data if isinstance(data, str) else json.dumps(data, default=json_serializer)
            await conn.execute(
                query,
                data_json,
                event_time,
                subscription_key,
            )
            logger.debug(f"已更新实时数据: {subscription_key}")

    async def get_all_subscriptions(self) -> List[dict]:
        """获取所有订阅键

        用于币安服务断线重连后恢复订阅。

        Returns:
            订阅列表，每个元素包含 subscription_key 和 data_type
        """
        query = """
            SELECT subscription_key, data_type, created_at
            FROM realtime_data
            ORDER BY created_at
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]

    def parse_subscription_key(self, subscription_key: str) -> dict:
        """解析订阅键

        订阅键格式：{EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]

        Args:
            subscription_key: 订阅键，如 "BINANCE:BTCUSDT@KLINE_1m"

        Returns:
            解析后的字典，包含：
            - exchange: 交易所（BINANCE）
            - symbol: 交易对（BTCUSDT）
            - product_suffix: 产品后缀（.PERP，可选）
            - data_type: 数据类型（KLINE）
            - interval: K线间隔（1m，可选）
            - raw: 原始订阅键

        Examples:
            >>> parse_subscription_key("BINANCE:BTCUSDT@KLINE_1m")
            {
                'exchange': 'BINANCE',
                'symbol': 'BTCUSDT',
                'product_suffix': None,
                'data_type': 'KLINE',
                'interval': '1m',
                'raw': 'BINANCE:BTCUSDT@KLINE_1m'
            }

            >>> parse_subscription_key("BINANCE:BTCUSDT.PERP@KLINE_60")
            {
                'exchange': 'BINANCE',
                'symbol': 'BTCUSDT.PERP',
                'product_suffix': '.PERP',
                'data_type': 'KLINE',
                'interval': '60',
                'raw': 'BINANCE:BTCUSDT.PERP@KLINE_60'
            }

            >>> parse_subscription_key("BINANCE:BTCUSDT@QUOTES")
            {
                'exchange': 'BINANCE',
                'symbol': 'BTCUSDT',
                'product_suffix': None,
                'data_type': 'QUOTES',
                'interval': None,
                'raw': 'BINANCE:BTCUSDT@QUOTES'
            }
        """
        result = {
            "exchange": "",
            "symbol": "",
            "product_suffix": None,
            "data_type": "",
            "interval": None,
            "raw": subscription_key,
        }

        # 解析交易所前缀
        # 初始化 rest 以避免 UnboundLocalError
        rest = subscription_key
        if ":" in subscription_key:
            exchange_part, rest = subscription_key.split(":", 1)
            result["exchange"] = exchange_part.upper()
        else:
            result["exchange"] = "BINANCE"  # 默认交易所

        # 解析数据部分
        if "@" in rest:
            symbol_part, data_type_part = rest.split("@", 1)
            result["symbol"] = symbol_part

            # 解析产品后缀
            if "." in symbol_part:
                symbol, suffix = symbol_part.split(".", 1)
                result["symbol"] = symbol
                result["product_suffix"] = f".{suffix}"

            # 解析数据类型和间隔
            if "_" in data_type_part:
                data_type, interval = data_type_part.split("_", 1)
                result["data_type"] = data_type.upper()
                result["interval"] = interval
            else:
                result["data_type"] = data_type_part.upper()
        else:
            # 没有 @，则整个都是symbol
            result["symbol"] = rest
            if "." in rest:
                symbol, suffix = rest.split(".", 1)
                result["symbol"] = symbol
                result["product_suffix"] = f".{suffix}"

        return result

    def subscription_key_to_binance_stream(self, subscription_key: str) -> tuple[str, bool]:
        """将订阅键转换为币安WS流名称

        Args:
            subscription_key: 订阅键，如 "BINANCE:BTCUSDT@KLINE_1" 或 "BINANCE:BTCUSDT.PERP@KLINE_1"

        Returns:
            tuple[str, bool]: (币安WS流名称, 是否为期货)
            - 币安WS流名称，如 "btcusdt@kline_1m"
            - 是否为期货，True 表示使用期货WS客户端

        说明：
        - 现货和期货都使用相同的WS流格式：btcusdt@kline_1m
        - 区分现货/期货通过选择不同的WS客户端
        - .PERP 后缀标识永续期货，使用期货WS客户端

        Examples:
            >>> subscription_key_to_binance_stream("BINANCE:BTCUSDT@KLINE_1")
            ('btcusdt@kline_1m', False)

            >>> subscription_key_to_binance_stream("BINANCE:BTCUSDT.PERP@KLINE_1")
            ('btcusdt@kline_1m', True)

            >>> subscription_key_to_binance_stream("BINANCE:BTCUSDT@QUOTES")
            ('btcusdt@ticker', False)
        """
        parsed = self.parse_subscription_key(subscription_key)

        # 获取产品后缀
        suffix = parsed.get("product_suffix", "")

        # 基础交易对
        symbol = parsed["symbol"].lower()

        # 数据类型和间隔
        data_type = parsed["data_type"].upper()
        interval_value = parsed.get("interval", "")

        # 转换间隔为币安格式
        binance_interval = resolution_to_interval(interval_value)

        # 添加期货标识（仅用于选择正确的WS客户端，WS流名不变）
        is_futures = suffix == ".PERP"

        if data_type == "KLINE":
            return f"{symbol}@kline_{binance_interval}", is_futures
        elif data_type in ("QUOTES", "TICKER"):
            return f"{symbol}@ticker", is_futures
        elif data_type == "TRADE":
            return f"{symbol}@trade", is_futures

        return f"{symbol}@{data_type.lower()}", is_futures
