"""
交易所信息模型

对应数据库 exchange_info 表的 Pydantic 模型。
包括交易对信息、搜索结果等。

作者: Claude Code
版本: v2.0.0
"""

import time
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ExchangeInfo(BaseModel):
    """
    交易所信息

    用于缓存交易所的完整信息。
    """

    exchange: str  # 交易所代码
    symbols: list[dict[str, Any]]  # 交易对列表
    cached_at: float  # 缓存时间戳

    def __str__(self) -> str:
        return f"ExchangeInfo({self.exchange}, {len(self.symbols)} symbols)"


class RichExchangeInfo(BaseModel):
    """
    完整的交易所信息模型

    用于表示完整的交易所信息，包括所有交易对。
    与 SymbolInfo（单个交易对详情）不同，RichExchangeInfo 包含所有交易对的信息。

    职责：
    1. 缓存完整的交易所信息（所有交易对）
    2. 提供交易对搜索和过滤功能
    3. 保持数据模型形式在项目内流转

    使用场景：
    - BinanceService.get_exchange_info() 返回类型
    - 缓存管理器存储格式
    - 交易对搜索的数据源
    """

    market_type: str  # 市场类型：现货 "spot" 或期货 "futures"
    exchange: str = "BINANCE"  # 交易所代码
    timezone: str = "UTC"  # 时区
    server_time: int | None = None  # 服务器时间（毫秒）
    symbols: list[dict[str, Any]]  # 所有交易对的原始数据
    cached_at: float = Field(default_factory=time.time)  # 缓存时间戳

    def get_symbol_count(self) -> int:
        """
        获取交易对数量

        Returns:
            int: 交易对总数
        """
        return len(self.symbols)

    def filter_symbols_by_status(self, status: str = "TRADING") -> list[dict[str, Any]]:
        """
        按状态过滤交易对

        Args:
            status: 交易状态，默认 "TRADING"

        Returns:
            List[Dict[str, Any]]: 符合状态的交易对列表
        """
        return [symbol for symbol in self.symbols if symbol.get("status") == status]

    def get_trading_symbols(self) -> list[str]:
        """
        获取所有可交易的交易对代码

        Returns:
            List[str]: 可交易的交易对代码列表
        """
        trading_symbols = self.filter_symbols_by_status("TRADING")
        return [symbol["symbol"] for symbol in trading_symbols if "symbol" in symbol]

    def find_symbol_by_name(self, symbol_name: str) -> dict[str, Any] | None:
        """
        根据交易对名称查找交易对信息

        Args:
            symbol_name: 交易对名称（如 "BTCUSDT"）

        Returns:
            Optional[Dict[str, Any]]: 交易对信息，如果未找到则返回 None
        """
        for symbol in self.symbols:
            if symbol.get("symbol") == symbol_name:
                return symbol
        return None

    def __str__(self) -> str:
        return f"RichExchangeInfo({self.market_type}, {self.exchange}, {len(self.symbols)} symbols)"


class SymbolMetadata(BaseModel):
    """
    交易对元数据

    用于内部管理的交易对元数据。
    """

    symbol: str  # 交易对
    exchange: str  # 交易所
    product_type: str  # 产品类型
    base_symbol: str  # 基础货币
    quote_symbol: str  # 计价货币
    status: str = "TRADING"  # 交易状态
    created_at: float | None = None  # 创建时间

    def __str__(self) -> str:
        return f"SymbolMetadata({self.symbol}, {self.product_type})"
