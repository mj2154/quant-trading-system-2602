"""
报价数据模型

TradingView 兼容的报价数据模型。

作者: Claude Code
版本: v2.0.0
"""

from pydantic import BaseModel


class QuotesValue(BaseModel):
    """
    统一报价值模型

    期货和现货共用的报价数据格式。
    符合TradingView quotes格式的字段结构。

    设计原则：
    - 统一格式：期货和现货使用相同的字段结构
    - 前端友好：只包含前端真正需要的字段
    - 简洁明了：去掉不必要的期货特有字段

    更新记录：
    - v2.1.0: 添加 short_name, exchange, description 字段以符合 TradingView API 规范
    """

    # 基础报价字段（前端真正需要的字段）
    ch: float  # 价格变化
    chp: float  # 价格变化百分比
    short_name: str  # 短名称（如 BTCUSDT）
    exchange: str  # 交易所名称（如 BINANCE）
    description: str  # 标的描述（如 比特币/泰达币）
    lp: float  # 最新价格（last price）
    ask: float  # 卖价
    bid: float  # 买价
    spread: float  # 价差
    open_price: float  # 开盘价
    high_price: float  # 最高价
    low_price: float  # 最低价
    prev_close_price: float | None = None  # 前收盘价 (WebSocket数据中可能缺失)
    volume: float  # 成交量


class QuotesData(BaseModel):
    """
    报价数据

    符合TradingView quotes API格式。
    使用简短字段名（n, s, v）以符合API规范。
    """

    n: str  # 标的全名（EXCHANGE:SYMBOL格式）
    s: str  # 状态（ok/error）
    v: QuotesValue  # 报价值对象

    def __str__(self) -> str:
        return f"QuotesData({self.n}, status={self.s})"


class QuotesList(BaseModel):
    """
    报价数据列表

    包含多个交易对的报价数据。
    """

    quotes: list[QuotesData]  # 报价数据列表

    def __str__(self) -> str:
        return f"QuotesList({len(self.quotes)} quotes)"


class PriceLevel(BaseModel):
    """
    价格层级

    用于订单簿深度数据。
    """

    price: float  # 价格
    quantity: float  # 数量

    def __str__(self) -> str:
        return f"PriceLevel({self.price}, {self.quantity})"


class OrderBookData(BaseModel):
    """
    订单簿数据

    包含买卖盘深度信息。
    """

    symbol: str  # 交易对
    bids: list[PriceLevel]  # 买盘（从高到低）
    asks: list[PriceLevel]  # 卖盘（从低到高）
    last_update_id: int  # 最后更新ID

    def __str__(self) -> str:
        return f"OrderBookData({self.symbol}, {len(self.bids)} bids, {len(self.asks)} asks)"
