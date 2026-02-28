"""
交易对数据模型

TradingView 兼容的交易对数据模型。

作者: Claude Code
版本: v2.0.0
"""

from pydantic import BaseModel


class SymbolInfo(BaseModel):
    """
    交易对详细信息

    完全符合 TradingView Charting Library 的 LibrarySymbolInfo 接口标准。
    基于官方文档：https://www.tradingview.com/charting-library-docs/latest/connecting_data/datafeed-api/required-methods
    """

    # 必需字段（无默认值）
    name: str  # 符号名称
    ticker: str  # 唯一标识符
    description: str  # 描述
    type: str  # 标的类型
    exchange: str  # 交易所
    listed_exchange: str  # 上市交易所
    session: str  # 交易时段
    timezone: str  # 时区
    minmov: float  # 最小变动单位
    pricescale: int  # 价格刻度

    # 官方标准字段（带默认值）
    base_name: list[str] | None = None
    long_description: str | None = None
    session_display: str | None = None
    session_holidays: str = ""
    corrections: str | None = None
    minmove2: float | None = None
    fractional: bool | None = None
    variable_tick_size: str | None = None
    has_intraday: bool = True
    has_seconds: bool = False
    has_ticks: bool = False
    seconds_multipliers: list[str] | None = None
    build_seconds_from_ticks: bool | None = None
    has_daily: bool = True
    daily_multipliers: list[str] = ["1"]
    has_weekly_and_monthly: bool = True
    weekly_multipliers: list[str] = ["1"]
    monthly_multipliers: list[str] = ["1"]
    has_empty_bars: bool = False
    visible_plots_set: str = "ohlcv"
    volume_precision: int = 0
    data_status: str = "streaming"
    delay: int = 0
    expired: bool = False
    expiration_date: int | None = None
    sector: str | None = None
    industry: str | None = None
    currency_code: str | None = None
    original_currency_code: str | None = None
    unit_id: str | None = None
    original_unit_id: str | None = None
    unit_conversion_types: list[str] | None = None
    subsession_id: str | None = None
    subsessions: list[dict[str, str]] | None = None
    price_source_id: str | None = None
    price_sources: list[dict[str, str]] | None = None
    logo_urls: list[str] | None = None
    format: str = "price"  # 格式（TradingView 标准）
    supported_resolutions: list[str] = []  # 支持的分辨率

    def __str__(self) -> str:
        return f"SymbolInfo({self.ticker}, {self.exchange})"


class SymbolSearchResult(BaseModel):
    """
    交易对搜索结果

    用于search_symbols API的返回结果。
    """

    symbol: str  # 交易对代码，如"BINANCE:BTCUSDT"
    full_name: str  # 全名，如"BINANCE:BTCUSDT"
    description: str  # 描述，如"BTC/USDT"
    exchange: str  # 交易所代码，如"BINANCE"
    ticker: str  # Ticker代码，如"BTCUSDT"
    type: str = "crypto"  # 类型，默认"crypto"

    def __str__(self) -> str:
        return f"SymbolSearchResult({self.symbol})"


class SymbolSearchResults(BaseModel):
    """
    交易对搜索结果列表

    包含搜索到的所有交易对。
    """

    symbols: list[SymbolSearchResult]  # 交易对列表
    total: int  # 总数量
    count: int  # 当前返回数量

    def __str__(self) -> str:
        return f"SymbolSearchResults({len(self.symbols)} results)"
