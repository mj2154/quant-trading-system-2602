"""
内部数据模型 - 用于数据库存储和内部数据传递

设计原则：
- 这些模型用于将外部API数据（币安）转换为内部存储格式
- 仅用于内部传递和数据库存储，不涉及前端接口
- 使用普通 BaseModel，不需要 camelCase 序列化

模型对应关系：
- InternalKlineData     -> klines_history 表
- InternalQuoteData      -> tasks.result 字段 (get_quotes 任务)
"""

from pydantic import BaseModel, Field


class InternalKlineData(BaseModel):
    """内部K线数据模型

    用于：
    1. 将币安12字段数组格式转换为扁平化结构
    2. 写入 klines_history 表

    表字段映射（klines_history）：
    - time                    -> open_time (毫秒时间戳转 TIMESTAMPTZ)
    - close_time              -> close_time (毫秒时间戳转 TIMESTAMPTZ)
    - open                    -> open_price
    - high                    -> high_price
    - low                     -> low_price
    - close                   -> close_price
    - volume                  -> volume
    - quote_volume            -> quote_volume
    - number_of_trades        -> number_of_trades
    - taker_buy_base_volume   -> taker_buy_base_volume
    - taker_buy_quote_volume  -> taker_buy_quote_volume
    - symbol                  -> symbol (带 BINANCE: 前缀)
    - interval                -> interval (TV格式)
    """

    time: int = Field(description="K线开始时间（毫秒时间戳）")
    close_time: int = Field(description="K线结束时间（毫秒时间戳）")
    open: float = Field(description="开盘价")
    high: float = Field(description="最高价")
    low: float = Field(description="最低价")
    close: float = Field(description="收盘价")
    volume: float = Field(description="成交量")
    quote_volume: float = Field(description="成交额")
    number_of_trades: int = Field(description="交易笔数")
    taker_buy_base_volume: float = Field(description="主动买入成交量")
    taker_buy_quote_volume: float = Field(description="主动买入成交额")
    symbol: str = Field(description="交易对符号（带 BINANCE: 前缀）")
    interval: str = Field(description="K线间隔（TV格式，如 1, 5, 15, 60, D）")


class InternalQuoteValues(BaseModel):
    """内部报价数值数据"""

    lp: float = Field(description="最新价格 (last price)")
    ch: float = Field(description="价格变动 (change)")
    chp: float = Field(description="价格变动百分比 (change percent)")
    high: float = Field(description="最高价")
    low: float = Field(description="最低价")
    volume: float = Field(description="成交量")
    quote_volume: float = Field(description="成交额")
    timestamp: int = Field(description="统计结束时间")


class InternalQuoteData(BaseModel):
    """内部报价数据模型

    用于：
    1. 将币安24hr ticker数据转换为内部格式
    2. 写入 tasks.result 字段 (get_quotes 任务)

    前端通过 tasks.result 获取数据后自行解析。
    """

    n: str = Field(description="交易对符号（带 BINANCE: 前缀）")
    s: str = Field(description="状态 (ok/error)")
    v: InternalQuoteValues = Field(description="报价数值数据")


class InternalQuotesResult(BaseModel):
    """内部报价结果模型 - 写入 tasks.result 字段"""

    quotes: list[InternalQuoteData] = Field(description="报价列表")
    count: int = Field(description="报价数量")
