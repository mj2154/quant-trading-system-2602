"""
交易所信息仓储

查询 exchange_info 表中的交易对信息。
"""


import asyncpg

from ..models.protocol.ws_payload import SymbolSearchItem
from ..models.trading.symbol_models import SymbolInfo


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
            symbol: 交易对字符串，如 "BINANCE:BTCUSDT" 或 "BINANCE:BTCUSDT.PERP"

        Returns:
            (exchange, ticker) 元组
        """
        if ":" in symbol:
            parts = symbol.split(":", 1)
            ticker = parts[1].upper()
            # 移除 .PERP 等合约类型后缀（数据库中不存储这些后缀）
            if "." in ticker:
                ticker = ticker.split(".")[0]
            return parts[0].upper(), ticker
        ticker = symbol.upper()
        # 移除 .PERP 等合约类型后缀
        if "." in ticker:
            ticker = ticker.split(".")[0]
        return "BINANCE", ticker

    async def resolve_symbol(
        self,
        symbol: str,
        exchange: str = "BINANCE",
        market_type: str = "SPOT",
    ) -> SymbolInfo | None:
        """精确解析单个交易对

        Args:
            symbol: 交易对字符串，支持 "EXCHANGE:SYMBOL" 格式
            exchange: 交易所代码
            market_type: 市场类型 (SPOT, FUTURES)

        Returns:
            SymbolInfo 模型实例，未找到返回 None
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

                # 返回 SymbolInfo 模型
                # 注意：ticker 必须是 EXCHANGE:SYMBOL 格式，符合 TradingView 要求
                # description 需要区分期货和现货：期货添加 .PERP 后缀
                symbol = row["symbol"]
                description = f"{symbol}.PERP" if market_type == "FUTURES" else symbol

                return SymbolInfo(
                    name=symbol,
                    ticker=f"{exchange}:{symbol}",  # 修复：添加交易所前缀
                    description=description,
                    exchange=exchange,
                    listed_exchange=exchange,
                    type="crypto",
                    session="24x7",
                    timezone="Etc/UTC",
                    minmov=1,
                    pricescale=100,
                    supported_resolutions=["1", "5", "15", "60", "240", "1D", "1W", "1M"],
                    intraday_multipliers=["1", "5", "15", "60"],
                    daily_multipliers=["1"],
                    weekly_multipliers=["1"],
                    monthly_multipliers=["1"],
                    has_intraday=True,
                    has_daily=True,
                    has_weekly_and_monthly=True,
                    visible_plots_set="ohlcv",
                    data_status="streaming",
                    volume_precision=2,
                    currency_code=row["quote_asset"],
                )
        except Exception:
            return None

    async def search_symbols(
        self,
        query: str = "",
        exchange: str = "BINANCE",
        market_type: str = "SPOT",
        limit: int = 50,
    ) -> list[SymbolSearchItem]:
        """搜索交易对

        Args:
            query: 搜索关键词
            exchange: 交易所代码
            market_type: 市场类型 (SPOT, FUTURES)
            limit: 返回数量限制

        Returns:
            SymbolSearchItem 列表
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
                symbol_suffix = ".PERP" if row["market_type"] == "FUTURES" else ""
                ticker = f"{row['symbol']}{symbol_suffix}"
                full_symbol = f"BINANCE:{ticker}"
                # description 使用商品代码（如 BTCUSDT），与现货/期货保持一致
                results.append(
                    SymbolSearchItem(
                        symbol=full_symbol,
                        full_name=full_symbol,  # TradingView格式: EXCHANGE:SYMBOL
                        description=ticker,
                        exchange="BINANCE",
                        ticker=ticker,
                        type="crypto",
                    )
                )

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
