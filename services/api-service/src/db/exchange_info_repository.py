"""
交易所信息仓储

查询 exchange_info 表中的交易对信息。
"""

import asyncpg
from typing import List, Dict, Any, Optional


class ExchangeInfoRepository:
    """交易所信息仓储"""

    def __init__(self, pool: asyncpg.Pool) -> None:
        """初始化仓储

        Args:
            pool: asyncpg 连接池
        """
        self._pool = pool

    def _parse_symbol(self, symbol: str) -> tuple[str, str]:
        """解析交易对字符串

        Args:
            symbol: 交易对字符串，如 "BINANCE:BTCUSDT" 或 "BTCUSDT"

        Returns:
            (exchange, ticker) 元组
        """
        if ":" in symbol:
            parts = symbol.split(":", 1)
            return parts[0].upper(), parts[1].upper()
        return "BINANCE", symbol.upper()

    async def resolve_symbol(
        self,
        symbol: str,
        exchange: str = "BINANCE",
        market_type: str = "SPOT",
    ) -> Optional[Dict[str, Any]]:
        """精确解析单个交易对

        Args:
            symbol: 交易对字符串，支持 "EXCHANGE:SYMBOL" 格式
            exchange: 交易所代码
            market_type: 市场类型 (SPOT, FUTURES)

        Returns:
            交易对信息字典，未找到返回 None
        """
        # 解析交易对字符串
        parsed_exchange, ticker = self._parse_symbol(symbol)

        # 使用解析出的交易所（如果有效）
        if parsed_exchange:
            exchange = parsed_exchange

        query_sql = """
            SELECT
                symbol,
                base_asset,
                quote_asset,
                status,
                quote_precision,
                base_asset_precision,
                filters,
                order_types,
                permissions,
                iceberg_allowed,
                oco_allowed,
                last_updated
            FROM exchange_info
            WHERE exchange = $1
              AND market_type = $2
              AND symbol = $3
            LIMIT 1
        """

        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    query_sql,
                    exchange,
                    market_type,
                    ticker,
                )

                if row is None:
                    return None

                full_symbol = f"{exchange}:{row['symbol']}"
                return {
                    "symbol": full_symbol,
                    "ticker": row['symbol'],
                    "name": row['symbol'],
                    "description": f"{row['base_asset']}/{row['quote_asset']}",
                    "exchange": exchange,
                    "listed_exchange": exchange,
                    "type": "crypto",
                    "session": "24x7",
                    "timezone": "Etc/UTC",
                    "minmov": 1,
                    "pricescale": 100,
                    "has_intraday": True,
                    "has_daily": True,
                    "has_weekly_and_monthly": True,
                    "volume_precision": 2,
                    "currency_code": row['quote_asset'],
                }
        except Exception:
            return None

    async def search_symbols(
        self,
        query: str = "",
        exchange: str = "BINANCE",
        market_type: str = "SPOT",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """搜索交易对

        Args:
            query: 搜索关键词
            exchange: 交易所代码
            market_type: 市场类型 (SPOT, FUTURES)
            limit: 返回数量限制

        Returns:
            交易对信息列表
        """
        query_sql = """
            SELECT
                symbol,
                base_asset,
                quote_asset,
                status,
                quote_precision,
                base_asset_precision,
                filters,
                order_types,
                permissions,
                iceberg_allowed,
                oco_allowed,
                last_updated,
                market_type
            FROM exchange_info
            WHERE exchange = $1
              AND market_type = $2
              AND (symbol ILIKE $3 OR base_asset ILIKE $3 OR quote_asset ILIKE $3)
            ORDER BY symbol
            LIMIT $4
        """

        search_pattern = f"%{query}%" if query else "%"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                query_sql,
                exchange,
                market_type,
                search_pattern,
                limit,
            )

            results = []
            for row in rows:
                # 永续期货添加 .PERP 后缀
                symbol_suffix = ".PERP" if row['market_type'] == "FUTURES" else ""
                ticker = f"{row['symbol']}{symbol_suffix}"
                full_symbol = f"BINANCE:{ticker}"
                results.append({
                    "symbol": full_symbol,
                    "full_name": full_symbol,  # TradingView格式: EXCHANGE:SYMBOL
                    "description": f"{row['base_asset']}/{row['quote_asset']}",
                    "exchange": "BINANCE",
                    "ticker": ticker,
                    "type": "crypto",
                })

            return results

    async def get_total_count(
        self,
        query: str = "",
        exchange: str = "BINANCE",
        market_type: str = "SPOT",
    ) -> int:
        """获取搜索结果的总数

        Args:
            query: 搜索关键词
            exchange: 交易所代码
            market_type: 市场类型

        Returns:
            总数量
        """
        query_sql = """
            SELECT COUNT(*)
            FROM exchange_info
            WHERE exchange = $1
              AND market_type = $2
              AND (symbol ILIKE $3 OR base_asset ILIKE $3 OR quote_asset ILIKE $3)
        """

        search_pattern = f"%{query}%" if query else "%"

        async with self._pool.acquire() as conn:
            count = await conn.fetchval(
                query_sql,
                exchange,
                market_type,
                search_pattern,
            )
            return count
