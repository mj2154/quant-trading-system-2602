"""
交易K线数据模型

TradingView 兼容的K线数据模型。

作者: Claude Code
版本: v2.0.0
"""

from pydantic import BaseModel, ConfigDict


class KlineBar(BaseModel):
    """
    K线Bar数据

    包含OHLCV（开高低收成交量）数据。
    """

    time: int  # Bar时间戳（毫秒）
    open: float  # 开盘价
    high: float  # 最高价
    low: float  # 最低价
    close: float  # 收盘价
    volume: float  # 成交量

    def __str__(self) -> str:
        return f"KlineBar(t={self.time}, o={self.open}, h={self.high}, l={self.low}, c={self.close}, v={self.volume})"


class KlineData(BaseModel):
    """
    单个K线数据

    包含Bar数据和元信息。
    """

    symbol: str  # 交易对，如"BINANCE:BTCUSDT"
    interval: str  # K线周期，如"1", "5", "60", "1D"（与数据库interval字段一致）
    bar: KlineBar  # Bar数据
    is_bar_closed: bool  # Bar是否已关闭

    model_config = ConfigDict(populate_by_name=True)

    def __str__(self) -> str:
        return f"KlineData({self.symbol}, {self.interval}, closed={self.is_bar_closed})"


class KlineBars(BaseModel):
    """
    K线数据列表

    包含多个K线Bar和元信息。
    """

    symbol: str  # 交易对
    interval: str  # K线周期，与数据库interval字段一致
    bars: list[KlineBar]  # Bar列表
    count: int  # Bar数量
    no_data: bool = False  # 是否无数据

    def __str__(self) -> str:
        return f"KlineBars({self.symbol}, {self.interval}, {len(self.bars)} bars)"


class KlineMeta(BaseModel):
    """
    K线元数据

    包含K线请求的元信息。
    """

    symbol: str  # 交易对
    interval: str  # K线周期，与数据库字段一致
    from_time: int | None = None  # 开始时间
    to: int | None = None  # 结束时间
    count: int  # Bar数量
    no_data: bool  # 是否无数据
    next_time: int | None = None  # 下一页时间

    def __str__(self) -> str:
        return f"KlineMeta({self.symbol}, {self.interval}, {self.count} bars)"


class KlineResponse(BaseModel):
    """
    K线响应数据

    包含K线数据和元信息，用于向后兼容。
    """

    data: list[KlineBar]  # K线数据列表
    meta: KlineMeta  # 元信息

    def __str__(self) -> str:
        return f"KlineResponse({self.meta.symbol}, {self.meta.resolution}, {len(self.data)} bars)"


# WebSocket K线数据别名
KlinesData = KlineBars
WSKlineData = KlineBar
