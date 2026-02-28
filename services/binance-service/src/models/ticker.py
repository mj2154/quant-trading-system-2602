"""
24hr Ticker数据模型

基于币安API的24小时价格变动统计。
支持现货(Spot)和期货(Futures)交易对。

遵循数据命名规范：
- SnakeCaseModel: 用于解析币安API响应，自动将camelCase转为snake_case

注意：
- 现货REST API使用camelCase字段名，可使用to_snake自动转换
- 期货REST API和WebSocket使用单字母字段名，需使用Field(alias=...)手动映射

API响应格式:
- 现货REST: GET https://api.binance.com/api/v3/ticker/24hr
- 期货REST: GET https://fapi.binance.com/fapi/v1/ticker/24hr
- 现货WS: <symbol>@ticker (wss://stream.binance.com:9443/ws/<symbol>@ticker)
- 期货WS: <symbol>@ticker (wss://ws-fapi.binance.com/ws-fapi/v1/<symbol>@ticker)

参考文档:
- 现货REST API: /home/ppadmin/code/binance-docs/binance_spot_docs/REST API/行情接口.md
- 期货REST API: /home/ppadmin/code/binance-docs/binance_futures_docs/U本位合约/REST API/行情接口.md
- 现货WS: /home/ppadmin/code/binance-docs/binance_spot_docs/WebSocket行情推送.md
- 期货WS: /home/ppadmin/code/binance-docs/binance_futures_docs/U本位合约/Websocket行情推送/按 Symbol 的完整 Ticker.md
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

# 使用本地基类
from .base import SnakeCaseModel


class Ticker24hrSpot(SnakeCaseModel):
    """
    现货24小时价格变动统计模型

    基于币安现货API 24hr ticker响应格式。
    使用SnakeCaseModel自动将camelCase字段转换为snake_case。

    响应示例:
    {
        "symbol": "BNBBTC",
        "priceChange": "-94.99999800",
        "priceChangePercent": "-95.960",
        "weightedAvgPrice": "0.29628482",
        "prevClosePrice": "0.10002000",
        "lastPrice": "4.00000200",
        "lastQty": "200.00000000",
        "bidPrice": "4.00000000",
        "bidQty": "100.00000000",
        "askPrice": "4.00000200",
        "askQty": "100.00000000",
        "openPrice": "99.00000000",
        "highPrice": "100.00000000",
        "lowPrice": "0.10000000",
        "volume": "8913.30000000",
        "quoteVolume": "15.30000000",
        "openTime": 1499783499040,
        "closeTime": 1499869899040,
        "firstId": 28385,
        "lastId": 28460,
        "count": 76
    }
    """

    # 交易对标识
    symbol: str

    # 价格变动 (camelCase -> snake_case 自动转换)
    price_change: Decimal
    price_change_percent: Decimal

    # 加权平均价格
    weighted_avg_price: Decimal

    # 上一收盘价（期货可能没有此字段）
    prev_close_price: Optional[Decimal] = None

    # 最近成交
    last_price: Decimal
    last_qty: Optional[Decimal] = None

    # 最优挂单（期货没有买卖盘字段）
    bid_price: Optional[Decimal] = None
    bid_qty: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    ask_qty: Optional[Decimal] = None

    # OHLC价格
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal

    # 成交量
    volume: Decimal
    quote_volume: Decimal

    # 时间信息
    open_time: int
    close_time: int

    # 成交ID统计
    first_id: int
    last_id: int
    count: int

    # ========== 验证器 ==========

    @field_validator(
        "price_change",
        "price_change_percent",
        "weighted_avg_price",
        "last_price",
        "open_price",
        "high_price",
        "low_price",
        "volume",
        "quote_volume",
        mode="before",
    )
    @classmethod
    def validate_required_decimal(cls, v):
        """验证并转换为Decimal类型（必需字段）"""
        if v is None:
            raise ValueError("必需价格字段不能为null")
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            return Decimal(v)
        return v

    @field_validator(
        "prev_close_price",
        "last_qty",
        "bid_price",
        "bid_qty",
        "ask_price",
        "ask_qty",
        mode="before",
    )
    @classmethod
    def validate_optional_decimal(cls, v):
        """验证并转换为Decimal类型（可选字段）"""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            return Decimal(v)
        return v

    @field_validator(
        "open_time", "close_time", "first_id", "last_id", "count", mode="before"
    )
    @classmethod
    def validate_required_int(cls, v):
        """验证并转换为int类型（必需字段）"""
        if v is None:
            raise ValueError("必需字段不能为null")
        return int(v)

    @field_validator("symbol", mode="before")
    @classmethod
    def validate_symbol(cls, v):
        """验证交易对符号"""
        if not v or not isinstance(v, str):
            raise ValueError("交易对符号不能为空")
        return v.upper()

    @model_validator(mode="after")
    def validate_price_consistency(self) -> "Ticker24hrSpot":
        """验证价格一致性"""
        if self.high_price < self.low_price:
            raise ValueError(
                f"high_price ({self.high_price}) must be >= low_price ({self.low_price})"
            )
        return self

    # ========== 计算属性 ==========

    @property
    def timestamp(self) -> int:
        """获取统计结束时间戳（毫秒）"""
        return self.close_time

    @property
    def datetime(self) -> datetime:
        """获取统计结束时间的datetime对象"""
        return datetime.fromtimestamp(self.close_time / 1000)


class Ticker24hrFutures(BaseModel):
    """
    期货24小时价格变动统计模型

    基于币安期货API 24hr ticker响应格式（单字符字段名）。

    响应示例:
    {
        "e": "24hrTicker",      // 事件类型
        "E": 123456789,         // 事件时间(毫秒)
        "s": "BNBUSDT",         // 交易对
        "p": "0.0015",          // 24小时价格变化
        "P": "250.00",          // 24小时价格变化(百分比)
        "w": "0.0018",          // 平均价格
        "c": "0.0025",          // 最新成交价格
        "Q": "10",              // 最新成交价格上的成交量
        "o": "0.0010",          // 24小时内第一笔成交的价格
        "h": "0.0025",          // 24小时内最高成交价
        "l": "0.0010",          // 24小时内最低成交价
        "v": "10000",           // 24小时内成交量
        "q": "18",              // 24小时内成交额
        "O": 0,                 // 统计开始时间
        "C": 86400000,          // 统计关闭时间
        "F": 0,                 // 24小时内第一笔成交交易ID
        "L": 18150,             // 24小时内最后一笔成交交易ID
        "n": 18151              // 24小时内成交数
    }
    """

    # 事件信息（可选）
    event_type: Optional[str] = Field(None, alias="e", description="事件类型")
    event_time: Optional[int] = Field(None, alias="E", description="事件时间(毫秒)")

    # 交易对标识
    symbol: str = Field(..., alias="s", description="交易对，如 BTCUSDT")

    # 价格变动（单字符字段名）
    price_change: Decimal = Field(..., alias="p", description="24小时内价格变化")
    price_change_percent: Decimal = Field(
        ..., alias="P", description="24小时内价格变化百分比"
    )

    # 加权平均价格
    weighted_avg_price: Decimal = Field(..., alias="w", description="平均价格")

    # 最近成交（单字符字段名）
    last_price: Decimal = Field(..., alias="c", description="最新成交价格")
    last_qty: Optional[Decimal] = Field(
        None, alias="Q", description="最新成交价格上的成交量"
    )

    # OHLC价格（单字符字段名）
    open_price: Decimal = Field(..., alias="o", description="24小时内第一笔成交的价格")
    high_price: Decimal = Field(..., alias="h", description="24小时内最高成交价")
    low_price: Decimal = Field(..., alias="l", description="24小时内最低成交价")

    # 成交量（单字符字段名）
    volume: Decimal = Field(..., alias="v", description="24小时内成交量")
    quote_volume: Decimal = Field(..., alias="q", description="24小时内成交额")

    # 时间信息（单字符字段名）
    open_time: Optional[int] = Field(None, alias="O", description="统计开始时间(毫秒)")
    close_time: int = Field(..., alias="C", description="统计关闭时间(毫秒)")

    # 成交ID统计（单字符字段名）
    first_id: Optional[int] = Field(
        None, alias="F", description="24小时内第一笔成交交易ID"
    )
    last_id: Optional[int] = Field(
        None, alias="L", description="24小时内最后一笔成交交易ID"
    )
    count: int = Field(..., alias="n", description="24小时内成交数")

    # ========== 验证器 ==========

    @field_validator(
        "price_change",
        "price_change_percent",
        "weighted_avg_price",
        "last_price",
        "last_qty",
        "open_price",
        "high_price",
        "low_price",
        "volume",
        "quote_volume",
        mode="before",
    )
    @classmethod
    def validate_decimal(cls, v):
        """验证并转换为Decimal类型，防止精度丢失"""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            return Decimal(v)
        return v

    @field_validator("close_time", "count", mode="before")
    @classmethod
    def validate_required_int(cls, v):
        """验证并转换为int类型（必需字段）"""
        if v is None:
            raise ValueError("必需字段不能为null")
        return int(v)

    @field_validator("open_time", "first_id", "last_id", mode="before")
    @classmethod
    def validate_optional_int(cls, v):
        """验证并转换为int类型（可选字段）"""
        if v is None:
            return None
        return int(v)

    @field_validator("symbol", mode="before")
    @classmethod
    def validate_symbol(cls, v):
        """验证交易对符号"""
        if not v or not isinstance(v, str):
            raise ValueError("交易对符号不能为空")
        return v.upper()

    @model_validator(mode="after")
    def validate_price_consistency(self) -> "Ticker24hrFutures":
        """验证价格一致性"""
        if self.high_price < self.low_price:
            raise ValueError(
                f"high_price ({self.high_price}) must be >= low_price ({self.low_price})"
            )
        return self

    # ========== 计算属性 ==========

    @property
    def timestamp(self) -> int:
        """获取统计结束时间戳（毫秒）"""
        return self.close_time

    @property
    def datetime(self) -> datetime:
        """获取统计结束时间的datetime对象"""
        return datetime.fromtimestamp(self.close_time / 1000)

    class Config:
        """Pydantic配置"""

        populate_by_name = True


class WebSocketTickerSpot(BaseModel):
    """
    现货WebSocket 24hr Ticker模型

    基于币安现货WebSocket推送的24hr ticker数据。
    Stream: <symbol>@ticker
    更新速度: 1000ms

    响应示例:
    {
        "e": "24hrTicker",      // 事件类型
        "E": 1672515782136,     // 事件时间
        "s": "BNBBTC",          // 交易对
        "p": "0.0015",          // 24小时价格变化
        "P": "250.00",          // 24小时价格变化（百分比）
        "w": "0.0018",          // 平均价格
        "x": "0.0009",          // 整整24小时之前，向前数的最后一次成交价格
        "c": "0.0025",          // 最新成交价格
        "Q": "10",              // 最新成交交易的成交量
        "b": "0.0024",          // 目前最高买单价
        "B": "10",              // 目前最高买单价的挂单量
        "a": "0.0026",          // 目前最低卖单价
        "A": "100",             // 目前最低卖单价的挂单量
        "o": "0.0010",          // 整整24小时前，向后数的第一次成交价格
        "h": "0.0025",          // 24小时内最高成交价
        "l": "0.0010",          // 24小时内最低成交价
        "v": "10000",           // 24小时内成交量
        "q": "18",              // 24小时内成交额
        "O": 0,                 // 统计开始时间
        "C": 1675216573749,     // 统计结束时间
        "F": 0,                 // 24小时内第一笔成交交易ID
        "L": 18150,             // 24小时内最后一笔成交交易ID
        "n": 18151              // 24小时内成交数
    }

    注意：现货WS ticker包含买卖盘深度字段(b, B, a, A)，期货WS ticker不包含这些字段。
    """

    # 事件信息
    event_type: str = Field(..., alias="e", description="事件类型，固定为 '24hrTicker'")
    event_time: int = Field(..., alias="E", description="事件时间(毫秒)")

    # 交易对标识
    symbol: str = Field(..., alias="s", description="交易对，如 BTCUSDT")

    # 价格变动
    price_change: Decimal = Field(..., alias="p", description="24小时价格变化")
    price_change_percent: Decimal = Field(
        ..., alias="P", description="24小时价格变化百分比"
    )

    # 加权平均价格
    weighted_avg_price: Decimal = Field(..., alias="w", description="平均价格")

    # 上一收盘价（WS推送特有）
    prev_price: Decimal = Field(
        ..., alias="x", description="整整24小时之前的最后一次成交价格"
    )

    # 最近成交
    last_price: Decimal = Field(..., alias="c", description="最新成交价格")
    last_qty: Decimal = Field(..., alias="Q", description="最新成交价格上的成交量")

    # 最优挂单（现货WS特有，期货没有）
    bid_price: Decimal = Field(..., alias="b", description="当前最高买单价")
    bid_qty: Decimal = Field(..., alias="B", description="当前最高买单价的挂单量")
    ask_price: Decimal = Field(..., alias="a", description="当前最低卖单价")
    ask_qty: Decimal = Field(..., alias="A", description="当前最低卖单价的挂单量")

    # OHLC价格
    open_price: Decimal = Field(..., alias="o", description="24小时开盘价")
    high_price: Decimal = Field(..., alias="h", description="24小时最高价")
    low_price: Decimal = Field(..., alias="l", description="24小时最低价")

    # 成交量
    volume: Decimal = Field(..., alias="v", description="24小时内成交量(基础资产)")
    quote_volume: Decimal = Field(
        ..., alias="q", description="24小时内成交额(报价资产)"
    )

    # 时间信息
    open_time: int = Field(..., alias="O", description="统计开始时间(毫秒)")
    close_time: int = Field(..., alias="C", description="统计结束时间(毫秒)")

    # 成交ID统计
    first_id: int = Field(..., alias="F", description="首笔成交ID")
    last_id: int = Field(..., alias="L", description="末笔成交ID")
    count: int = Field(..., alias="n", description="成交数")

    # ========== 验证器 ==========

    @field_validator(
        "price_change",
        "price_change_percent",
        "weighted_avg_price",
        "prev_price",
        "last_price",
        "last_qty",
        "bid_price",
        "bid_qty",
        "ask_price",
        "ask_qty",
        "open_price",
        "high_price",
        "low_price",
        "volume",
        "quote_volume",
        mode="before",
    )
    @classmethod
    def validate_decimal(cls, v):
        """验证并转换为Decimal类型"""
        if v is None:
            raise ValueError("价格/数量字段不能为null")
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            return Decimal(v)
        return v

    @field_validator(
        "event_time",
        "open_time",
        "close_time",
        "first_id",
        "last_id",
        "count",
        mode="before",
    )
    @classmethod
    def validate_int(cls, v):
        """验证并转换为int类型"""
        if v is None:
            raise ValueError("必需字段不能为null")
        return int(v)

    @field_validator("symbol", mode="before")
    @classmethod
    def validate_symbol(cls, v):
        """验证交易对符号"""
        if not v or not isinstance(v, str):
            raise ValueError("交易对符号不能为空")
        return v.upper()

    @model_validator(mode="after")
    def validate_price_consistency(self) -> "WebSocketTickerSpot":
        """验证价格一致性"""
        if self.high_price < self.low_price:
            raise ValueError(
                f"high_price ({self.high_price}) must be >= low_price ({self.low_price})"
            )
        return self

    # ========== 计算属性 ==========

    @property
    def timestamp(self) -> int:
        """获取事件时间戳（毫秒）"""
        return self.event_time

    @property
    def datetime(self) -> datetime:
        """获取事件时间的datetime对象"""
        return datetime.fromtimestamp(self.event_time / 1000)

    class Config:
        """Pydantic配置"""

        populate_by_name = True


class WebSocketTickerFutures(BaseModel):
    """
    期货WebSocket 24hr Ticker模型

    基于币安期货WebSocket推送的24hr ticker数据。
    Stream: <symbol>@ticker
    更新速度: 2000ms

    响应示例:
    {
        "e": "24hrTicker",      // 事件类型
        "E": 123456789,         // 事件时间(毫秒)
        "s": "BNBUSDT",         // 交易对
        "p": "0.0015",         // 24小时价格变化
        "P": "250.00",         // 24小时价格变化百分比
        "w": "0.0018",         // 平均价格
        "c": "0.0025",         // 最新成交价格
        "Q": "10",             // 最新成交价格上的成交量
        "o": "0.0010",         // 24小时内第一笔成交的价格
        "h": "0.0025",         // 24小时内最高成交价
        "l": "0.0010",         // 24小时内最低成交价
        "v": "10000",          // 24小时内成交量
        "q": "18",             // 24小时内成交额
        "O": 0,                // 统计开始时间
        "C": 86400000,         // 统计关闭时间
        "F": 0,               // 24小时内第一笔成交交易ID
        "L": 18150,           // 24小时内最后一笔成交交易ID
        "n": 18151            // 24小时内成交数
    }

    注意：期货WS ticker不包含买卖盘深度字段(x, b, B, a, A)，现货WS ticker包含这些字段。
    """

    # 事件信息
    event_type: str = Field(..., alias="e", description="事件类型，固定为 '24hrTicker'")
    event_time: int = Field(..., alias="E", description="事件时间(毫秒)")

    # 交易对标识
    symbol: str = Field(..., alias="s", description="交易对，如 BTCUSDT")

    # 价格变动
    price_change: Decimal = Field(..., alias="p", description="24小时价格变化")
    price_change_percent: Decimal = Field(
        ..., alias="P", description="24小时价格变化百分比"
    )

    # 加权平均价格
    weighted_avg_price: Decimal = Field(..., alias="w", description="平均价格")

    # 最近成交
    last_price: Decimal = Field(..., alias="c", description="最新成交价格")
    last_qty: Decimal = Field(..., alias="Q", description="最新成交价格上的成交量")

    # OHLC价格
    open_price: Decimal = Field(..., alias="o", description="24小时开盘价")
    high_price: Decimal = Field(..., alias="h", description="24小时最高价")
    low_price: Decimal = Field(..., alias="l", description="24小时最低价")

    # 成交量
    volume: Decimal = Field(..., alias="v", description="24小时内成交量(基础资产)")
    quote_volume: Decimal = Field(
        ..., alias="q", description="24小时内成交额(报价资产)"
    )

    # 时间信息
    open_time: int = Field(..., alias="O", description="统计开始时间(毫秒)")
    close_time: int = Field(..., alias="C", description="统计结束时间(毫秒)")

    # 成交ID统计
    first_id: int = Field(..., alias="F", description="首笔成交ID")
    last_id: int = Field(..., alias="L", description="末笔成交ID")
    count: int = Field(..., alias="n", description="成交数")

    # ========== 验证器 ==========

    @field_validator(
        "price_change",
        "price_change_percent",
        "weighted_avg_price",
        "last_price",
        "last_qty",
        "open_price",
        "high_price",
        "low_price",
        "volume",
        "quote_volume",
        mode="before",
    )
    @classmethod
    def validate_decimal(cls, v):
        """验证并转换为Decimal类型"""
        if v is None:
            raise ValueError("价格/数量字段不能为null")
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            return Decimal(v)
        return v

    @field_validator(
        "event_time",
        "open_time",
        "close_time",
        "first_id",
        "last_id",
        "count",
        mode="before",
    )
    @classmethod
    def validate_int(cls, v):
        """验证并转换为int类型"""
        if v is None:
            raise ValueError("必需字段不能为null")
        return int(v)

    @field_validator("symbol", mode="before")
    @classmethod
    def validate_symbol(cls, v):
        """验证交易对符号"""
        if not v or not isinstance(v, str):
            raise ValueError("交易对符号不能为空")
        return v.upper()

    @model_validator(mode="after")
    def validate_price_consistency(self) -> "WebSocketTickerFutures":
        """验证价格一致性"""
        if self.high_price < self.low_price:
            raise ValueError(
                f"high_price ({self.high_price}) must be >= low_price ({self.low_price})"
            )
        return self

    # ========== 计算属性 ==========

    @property
    def timestamp(self) -> int:
        """获取事件时间戳（毫秒）"""
        return self.event_time

    @property
    def datetime(self) -> datetime:
        """获取事件时间的datetime对象"""
        return datetime.fromtimestamp(self.event_time / 1000)

    class Config:
        """Pydantic配置"""

        populate_by_name = True


class Ticker24hrMini(BaseModel):
    """
    24小时价格变动统计精简模型

    用于MINI类型的API响应（字段更少）。

    响应示例:
    {
        "symbol": "BNBBTC",
        "openPrice": "99.00000000",
        "highPrice": "100.00000000",
        "lowPrice": "0.10000000",
        "lastPrice": "4.00000200",
        "volume": "8913.30000000",
        "quoteVolume": "15.30000000",
        "openTime": 1499783499040,
        "closeTime": 1499869899040,
        "firstId": 28385,
        "lastId": 28460,
        "count": 76
    }
    """

    symbol: str = Field(..., description="交易对符号")

    open_price: Decimal = Field(..., alias="openPrice", description="24小时开盘价")
    high_price: Decimal = Field(..., alias="highPrice", description="24小时最高价")
    low_price: Decimal = Field(..., alias="lowPrice", description="24小时最低价")
    last_price: Decimal = Field(..., alias="lastPrice", description="最近一次成交价")

    volume: Decimal = Field(..., description="24小时成交量(基础资产)")
    quote_volume: Decimal = Field(
        ..., alias="quoteVolume", description="24小时成交额(报价资产)"
    )

    open_time: int = Field(..., alias="openTime", description="开始时间戳")
    close_time: int = Field(..., alias="closeTime", description="结束时间戳")

    first_id: int = Field(..., alias="firstId", description="首笔成交ID")
    last_id: int = Field(..., alias="lastId", description="末笔成交ID")
    count: int = Field(..., description="成交笔数")

    @field_validator(
        "open_price",
        "high_price",
        "low_price",
        "last_price",
        "volume",
        "quote_volume",
        mode="before",
    )
    @classmethod
    def validate_decimal(cls, v):
        """验证并转换为Decimal类型"""
        if v is None:
            raise ValueError("价格/数量字段不能为null")
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            return Decimal(v)
        return v

    @field_validator(
        "open_time", "close_time", "first_id", "last_id", "count", mode="before"
    )
    @classmethod
    def validate_int(cls, v):
        """验证并转换为int类型"""
        if v is None:
            raise ValueError("整数字段不能为null")
        return int(v)

    @model_validator(mode="after")
    def validate_price_consistency(self) -> "Ticker24hrMini":
        """验证价格一致性"""
        if self.high_price < self.low_price:
            raise ValueError(
                f"high_price ({self.high_price}) must be >= low_price ({self.low_price})"
            )
        return self

    class Config:
        """Pydantic配置"""

        populate_by_name = True
