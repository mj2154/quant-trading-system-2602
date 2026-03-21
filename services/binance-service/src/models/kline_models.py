"""
K线数据模型

严格遵循币安官方文档格式。

文档来源:
- 现货 K线 GET: binance_spot_docs/01_REST API/Market Data endpoints.md
- 现货 K线 WS: binance_spot_docs/WebSocket Streams.md
- 期货 K线 GET: binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/K 线数据.md
- 期货 K线 WS: binance_futures_docs/01_U本位合约/02_Websocket行情推送/K线.md
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# 现货 K线
# =============================================================================


class BinanceSpotKlineGetModel(BaseModel):
    """现货 K线 GET 响应模型

    接口: GET /api/v3/klines
    特点: 数组格式，按索引访问
    文档来源: binance_spot_docs/01_REST API/Market Data endpoints.md
    """

    open_time: int = Field(alias="0", description="K线开始时间")
    open_price: Decimal = Field(alias="1", description="开盘价")
    high_price: Decimal = Field(alias="2", description="最高价")
    low_price: Decimal = Field(alias="3", description="最低价")
    close_price: Decimal = Field(alias="4", description="收盘价")
    volume: Decimal = Field(alias="5", description="成交量")
    close_time: int = Field(alias="6", description="K线结束时间")
    quote_volume: Decimal = Field(alias="7", description="成交额")
    number_of_trades: int = Field(alias="8", description="交易笔数")
    taker_buy_base_volume: Decimal = Field(alias="9", description="主动买入成交量")
    taker_buy_quote_volume: Decimal = Field(alias="10", description="主动买入成交额")
    unused: str = Field(alias="11", description="未使用字段")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotKlineWSData(BaseModel):
    """现货 K线 WS 内部数据模型

    文档来源: binance_spot_docs/WebSocket Streams.md
    """

    open_time: int = Field(alias="t", description="K线开始时间")
    close_time: int = Field(alias="T", description="K线结束时间")
    symbol: str = Field(alias="s", description="交易对")
    interval: str = Field(alias="i", description="K线间隔")
    first_trade_id: int = Field(alias="f", description="第一笔成交ID")
    last_trade_id: int = Field(alias="L", description="最后一笔成交ID")
    open_price: Decimal = Field(alias="o", description="开盘价")
    close_price: Decimal = Field(alias="c", description="收盘价")
    high_price: Decimal = Field(alias="h", description="最高价")
    low_price: Decimal = Field(alias="l", description="最低价")
    volume: Decimal = Field(alias="v", description="成交量")
    number_of_trades: int = Field(alias="n", description="交易笔数")
    is_closed: bool = Field(alias="x", description="K线是否已结束")
    quote_volume: Decimal = Field(alias="q", description="成交额")
    taker_buy_base_volume: Decimal = Field(alias="V", description="主动买入成交量")
    taker_buy_quote_volume: Decimal = Field(alias="Q", description="主动买入成交额")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotKlineWSModel(BaseModel):
    """现货 K线 WS 事件模型

    文档来源: binance_spot_docs/WebSocket Streams.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    symbol: str = Field(alias="s", description="交易对")
    kline: BinanceSpotKlineWSData = Field(alias="k", description="K线数据")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货 K线
# =============================================================================


class BinanceFuturesKlineGetModel(BaseModel):
    """期货 K线 GET 响应模型

    接口: GET /fapi/v1/klines
    特点: 数组格式，按索引访问
    文档来源: binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/K 线数据.md
    """

    open_time: int = Field(alias="0", description="K线开始时间")
    open_price: Decimal = Field(alias="1", description="开盘价")
    high_price: Decimal = Field(alias="2", description="最高价")
    low_price: Decimal = Field(alias="3", description="最低价")
    close_price: Decimal = Field(alias="4", description="收盘价")
    volume: Decimal = Field(alias="5", description="成交量")
    close_time: int = Field(alias="6", description="K线结束时间")
    quote_volume: Decimal = Field(alias="7", description="成交额")
    number_of_trades: int = Field(alias="8", description="交易笔数")
    taker_buy_base_volume: Decimal = Field(alias="9", description="主动买入成交量")
    taker_buy_quote_volume: Decimal = Field(alias="10", description="主动买入成交额")
    unused: str = Field(alias="11", description="忽略字段")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesKlineWSData(BaseModel):
    """期货 K线 WS 内部数据模型

    文档来源: binance_futures_docs/01_U本位合约/02_Websocket行情推送/K线.md
    """

    open_time: int = Field(alias="t", description="K线开始时间")
    close_time: int = Field(alias="T", description="K线结束时间")
    symbol: str = Field(alias="s", description="交易对")
    interval: str = Field(alias="i", description="K线间隔")
    first_trade_id: int = Field(alias="f", description="第一笔成交ID")
    last_trade_id: int = Field(alias="L", description="最后一笔成交ID")
    open_price: Decimal = Field(alias="o", description="开盘价")
    close_price: Decimal = Field(alias="c", description="收盘价")
    high_price: Decimal = Field(alias="h", description="最高价")
    low_price: Decimal = Field(alias="l", description="最低价")
    volume: Decimal = Field(alias="v", description="成交量")
    number_of_trades: int = Field(alias="n", description="交易笔数")
    is_closed: bool = Field(alias="x", description="K线是否已结束")
    quote_volume: Decimal = Field(alias="q", description="成交额")
    taker_buy_base_volume: Decimal = Field(alias="V", description="主动买入成交量")
    taker_buy_quote_volume: Decimal = Field(alias="Q", description="主动买入成交额")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesKlineWSModel(BaseModel):
    """期货 K线 WS 事件模型

    文档来源: binance_futures_docs/01_U本位合约/02_Websocket行情推送/K线.md
    """

    event_type: str = Field(alias="e", description="事件类型")
    event_time: int = Field(alias="E", description="事件时间")
    symbol: str = Field(alias="s", description="交易对")
    kline: BinanceFuturesKlineWSData = Field(alias="k", description="K线数据")

    model_config = ConfigDict(populate_by_name=True)
