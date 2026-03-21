"""
24hr Ticker数据模型

严格遵循币安官方文档格式。

文档来源:
- 现货 GET 24hr: binance_spot_docs/01_REST API/Market Data endpoints.md
- 现货 WS 24hr: binance_spot_docs/WebSocket Streams.md
- 期货 GET 24hr: binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/24hr价格变动情况.md
- 期货 WS 24hr: binance_futures_docs/01_U本位合约/02_Websocket行情推送/按 Symbol 的完整 Ticker.md
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# 现货 24hr Ticker
# =============================================================================


class BinanceSpotTicker24hrGetModel(BaseModel):
    """现货 24hr Ticker GET 响应模型

    接口: GET /api/v3/ticker/24hr
    文档来源: binance_spot_docs/01_REST API/Market Data endpoints.md
    """

    symbol: str = Field(description="交易对")
    price_change: Decimal = Field(alias="priceChange", description="价格变动")
    price_change_percent: Decimal = Field(
        alias="priceChangePercent", description="价格变动百分比"
    )
    weighted_avg_price: Decimal = Field(
        alias="weightedAvgPrice", description="加权平均价格"
    )
    prev_close_price: Decimal = Field(alias="prevClosePrice", description="前一日收盘价")
    last_price: Decimal = Field(alias="lastPrice", description="最新价格")
    last_qty: Decimal = Field(alias="lastQty", description="最新成交量")
    bid_price: Decimal = Field(alias="bidPrice", description="最佳买价")
    bid_qty: Decimal = Field(alias="bidQty", description="最佳买量")
    ask_price: Decimal = Field(alias="askPrice", description="最佳卖价")
    ask_qty: Decimal = Field(alias="askQty", description="最佳卖量")
    open_price: Decimal = Field(alias="openPrice", description="开盘价")
    high_price: Decimal = Field(alias="highPrice", description="最高价")
    low_price: Decimal = Field(alias="lowPrice", description="最低价")
    volume: Decimal = Field(description="成交量")
    quote_volume: Decimal = Field(alias="quoteVolume", description="成交额")
    open_time: int = Field(alias="openTime", description="统计开始时间")
    close_time: int = Field(alias="closeTime", description="统计结束时间")
    first_id: int = Field(alias="firstId", description="首笔成交ID")
    last_id: int = Field(alias="lastId", description="末笔成交ID")
    count: int = Field(description="成交笔数")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotTicker24hrWSModel(BaseModel):
    """现货 24hr Ticker WS 事件模型

    Stream: <symbol>@ticker
    文档来源: binance_spot_docs/WebSocket Streams.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    symbol: str = Field(alias="s", description="交易对")
    price_change: Decimal = Field(alias="p", description="价格变动")
    price_change_percent: Decimal = Field(alias="P", description="价格变动百分比")
    weighted_avg_price: Decimal = Field(alias="w", description="加权平均价格")
    first_price: Decimal = Field(alias="x", description="First trade(F)-1 price")
    last_price: Decimal = Field(alias="c", description="最新价格")
    last_qty: Decimal = Field(alias="Q", description="最新成交量")
    best_bid_price: Decimal = Field(alias="b", description="最佳买价")
    best_bid_qty: Decimal = Field(alias="B", description="最佳买量")
    best_ask_price: Decimal = Field(alias="a", description="最佳卖价")
    best_ask_qty: Decimal = Field(alias="A", description="最佳卖量")
    open_price: Decimal = Field(alias="o", description="开盘价")
    high_price: Decimal = Field(alias="h", description="最高价")
    low_price: Decimal = Field(alias="l", description="最低价")
    volume: Decimal = Field(alias="v", description="成交量")
    quote_volume: Decimal = Field(alias="q", description="成交额")
    open_time: int = Field(alias="O", description="统计开始时间")
    close_time: int = Field(alias="C", description="统计结束时间")
    first_trade_id: int = Field(alias="F", description="首笔成交ID")
    last_trade_id: int = Field(alias="L", description="末笔成交ID")
    number_of_trades: int = Field(alias="n", description="成交笔数")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货 24hr Ticker
# =============================================================================


class BinanceFuturesTicker24hrGetModel(BaseModel):
    """期货 24hr Ticker GET 响应模型

    接口: GET /fapi/v1/ticker/24hr
    文档来源: binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/24hr价格变动情况.md
    """

    symbol: str = Field(description="交易对")
    price_change: Decimal = Field(alias="priceChange", description="价格变动")
    price_change_percent: Decimal = Field(
        alias="priceChangePercent", description="价格变动百分比"
    )
    weighted_avg_price: Decimal = Field(
        alias="weightedAvgPrice", description="加权平均价格"
    )
    last_price: Decimal = Field(alias="lastPrice", description="最新价格")
    last_qty: Decimal = Field(alias="lastQty", description="最新成交量")
    open_price: Decimal = Field(alias="openPrice", description="开盘价")
    high_price: Decimal = Field(alias="highPrice", description="最高价")
    low_price: Decimal = Field(alias="lowPrice", description="最低价")
    volume: Decimal = Field(description="成交量")
    quote_volume: Decimal = Field(alias="quoteVolume", description="成交额")
    open_time: int = Field(alias="openTime", description="统计开始时间")
    close_time: int = Field(alias="closeTime", description="统计结束时间")
    first_id: int = Field(alias="firstId", description="首笔成交ID")
    last_id: int = Field(alias="lastId", description="末笔成交ID")
    count: int = Field(description="成交笔数")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesTicker24hrWSModel(BaseModel):
    """期货 24hr Ticker WS 事件模型

    Stream: <symbol>@ticker
    文档来源: binance_futures_docs/01_U本位合约/02_Websocket行情推送/按 Symbol 的完整 Ticker.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    symbol: str = Field(alias="s", description="交易对")
    price_change: Decimal = Field(alias="p", description="价格变动")
    price_change_percent: Decimal = Field(alias="P", description="价格变动百分比")
    weighted_avg_price: Decimal = Field(alias="w", description="加权平均价格")
    last_price: Decimal = Field(alias="c", description="最新价格")
    last_qty: Decimal = Field(alias="Q", description="最新成交量")
    open_price: Decimal = Field(alias="o", description="开盘价")
    high_price: Decimal = Field(alias="h", description="最高价")
    low_price: Decimal = Field(alias="l", description="最低价")
    volume: Decimal = Field(alias="v", description="成交量")
    quote_volume: Decimal = Field(alias="q", description="成交额")
    open_time: int = Field(alias="O", description="统计开始时间")
    close_time: int = Field(alias="C", description="统计结束时间")
    first_trade_id: int = Field(alias="F", description="首笔成交ID")
    last_trade_id: int = Field(alias="L", description="末笔成交ID")
    number_of_trades: int = Field(alias="n", description="成交笔数")

    model_config = ConfigDict(populate_by_name=True)
