"""
K线数据模型

基于币安API的K线数据模型，支持现货和期货交易对。
使用Pydantic V2进行数据验证和序列化。

遵循数据命名规范：
- SnakeCaseModel: 用于解析币安API响应，自动将camelCase转为snake_case

优化点：
- 提取 KlineValidatorMixin 共享验证器
- 移除重复的验证逻辑代码
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# 使用本地基类
from .base import SnakeCaseModel


# ========== 共享验证器 Mixin ==========

class KlineValidatorMixin:
    """K线数据验证器 Mixin

    包含价格验证、成交量验证、时间验证和OHLC一致性验证。
    供所有K线相关模型类使用。
    """

    @staticmethod
    def _validate_price(v):
        """验证并转换价格为Decimal类型"""
        if isinstance(v, str) or isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

    @staticmethod
    def _validate_volume(v):
        """验证并转换量为Decimal类型"""
        if isinstance(v, str) or isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

    @staticmethod
    def _validate_datetime(v):
        """验证并转换时间为datetime类型"""
        if isinstance(v, int):
            return datetime.fromtimestamp(v / 1000)
        if isinstance(v, str):
            return datetime.fromtimestamp(int(v) / 1000)
        return v

    @staticmethod
    def _validate_ohlc_consistency(self) -> None:
        """验证OHLC价格的一致性"""
        if self.high_price < self.open_price:
            raise ValueError(
                f"high_price ({self.high_price}) must be >= open_price ({self.open_price})"
            )
        if self.high_price < self.close_price:
            raise ValueError(
                f"high_price ({self.high_price}) must be >= close_price ({self.close_price})"
            )
        if self.high_price < self.low_price:
            raise ValueError(
                f"high_price ({self.high_price}) must be >= low_price ({self.low_price})"
            )
        if self.low_price > self.open_price:
            raise ValueError(
                f"low_price ({self.low_price}) must be <= open_price ({self.open_price})"
            )
        if self.low_price > self.close_price:
            raise ValueError(
                f"low_price ({self.low_price}) must be <= close_price ({self.close_price})"
            )
        if self.low_price > self.high_price:
            raise ValueError(
                f"low_price ({self.low_price}) must be <= high_price ({self.high_price})"
            )

    @staticmethod
    def _validate_time_consistency(self) -> None:
        """验证时间字段的一致性"""
        if self.open_time > self.close_time:
            raise ValueError(
                f"open_time ({self.open_time}) must be <= close_time ({self.close_time})"
            )


# ========== K线数据模型 ==========

class KlineData(KlineValidatorMixin, BaseModel):
    """
    K线数据模型

    表示一根K线的所有数据，包括OHLCV价格信息、成交量、交易次数等。

    基于币安API的K线数据格式:
    - REST API: 数组格式 [open_time, open, high, low, close, volume, ...]
    - WebSocket: JSON格式 {"t": start_time, "o": open, "h": high, ...}
    """

    # 基础时间信息
    open_time: datetime = Field(..., description="K线开始时间")
    close_time: datetime = Field(..., description="K线结束时间")

    # 交易对和间隔
    symbol: str = Field(
        ...,
        description="语义化交易对符号，格式: EXCHANGE:SYMBOL[.CONTRACT_TYPE]，"
                    "例如: BINANCE:BTCUSDT (现货), BINANCE:BTCUSDT.PERP (永续合约)"
    )
    interval: str = Field(..., description="K线间隔，如1m, 5m, 1h, 1d")

    # OHLC价格信息
    open_price: Decimal = Field(..., ge=0, description="开盘价，必须大于等于0")
    high_price: Decimal = Field(..., ge=0, description="最高价，必须大于等于0")
    low_price: Decimal = Field(..., ge=0, description="最低价，必须大于等于0")
    close_price: Decimal = Field(..., ge=0, description="收盘价，必须大于等于0")

    # 成交量信息
    volume: Decimal = Field(..., ge=0, description="成交量（基础资产），必须大于等于0")
    quote_volume: Decimal = Field(..., ge=0, description="成交额（报价资产），必须大于等于0")

    # 交易统计
    number_of_trades: int = Field(..., ge=0, description="交易笔数，必须大于等于0")

    # Taker买入统计
    taker_buy_base_volume: Decimal = Field(
        default=Decimal("0"), ge=0, description="主动买入成交量（基础资产）"
    )
    taker_buy_quote_volume: Decimal = Field(
        default=Decimal("0"), ge=0, description="主动买入成交额（报价资产）"
    )

    # WebSocket特有字段
    first_trade_id: Optional[int] = Field(None, ge=0, description="第一笔交易ID")
    last_trade_id: Optional[int] = Field(None, ge=0, description="最后一笔交易ID")
    is_closed: Optional[bool] = Field(None, description="K线是否已结束")

    # 事件时间（WebSocket）
    event_time: Optional[datetime] = Field(None, description="事件发生时间")

    @field_validator("open_price", "high_price", "low_price", "close_price", mode="before")
    @classmethod
    def _validate_price_wrapper(cls, v):
        return cls._validate_price(v)

    @field_validator("volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume", mode="before")
    @classmethod
    def _validate_volume_wrapper(cls, v):
        return cls._validate_volume(v)

    @field_validator("open_time", "close_time", "event_time", mode="before")
    @classmethod
    def _validate_datetime_wrapper(cls, v):
        return cls._validate_datetime(v)

    @model_validator(mode="after")
    def validate_all(self) -> "KlineData":
        self._validate_ohlc_consistency(self)
        self._validate_time_consistency(self)
        return self

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: str(v), datetime: lambda v: int(v.timestamp() * 1000)},
        populate_by_name=True,
    )


class KlineCreate(KlineValidatorMixin, BaseModel):
    """
    创建K线数据的模型

    用于向数据库插入新的K线记录
    """

    symbol: str = Field(
        ...,
        description="语义化交易对符号，格式: EXCHANGE:SYMBOL[.CONTRACT_TYPE]"
    )
    interval: str = Field(..., description="K线间隔")

    open_time: datetime = Field(..., description="K线开始时间")
    close_time: datetime = Field(..., description="K线结束时间")

    open_price: Decimal = Field(..., ge=0, description="开盘价")
    high_price: Decimal = Field(..., ge=0, description="最高价")
    low_price: Decimal = Field(..., ge=0, description="最低价")
    close_price: Decimal = Field(..., ge=0, description="收盘价")

    volume: Decimal = Field(..., ge=0, description="成交量")
    quote_volume: Decimal = Field(..., ge=0, description="成交额")

    number_of_trades: int = Field(..., ge=0, description="交易笔数")

    taker_buy_base_volume: Decimal = Field(default=Decimal("0"), ge=0, description="主动买入成交量")
    taker_buy_quote_volume: Decimal = Field(default=Decimal("0"), ge=0, description="主动买入成交额")

    first_trade_id: Optional[int] = Field(None, ge=0, description="第一笔交易ID")
    last_trade_id: Optional[int] = Field(None, ge=0, description="最后一笔交易ID")
    is_closed: bool = Field(default=False, description="K线是否已结束")

    @field_validator("open_price", "high_price", "low_price", "close_price", mode="before")
    @classmethod
    def _validate_price_wrapper(cls, v):
        return cls._validate_price(v)

    @field_validator("volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume", mode="before")
    @classmethod
    def _validate_volume_wrapper(cls, v):
        return cls._validate_volume(v)

    @model_validator(mode="after")
    def validate_all(self) -> "KlineCreate":
        self._validate_ohlc_consistency(self)
        self._validate_time_consistency(self)
        return self

    def to_kline_data(self) -> KlineData:
        """转换为 KlineData 模型"""
        return KlineData(
            symbol=self.symbol,
            interval=self.interval,
            open_time=self.open_time,
            close_time=self.close_time,
            open_price=self.open_price,
            high_price=self.high_price,
            low_price=self.low_price,
            close_price=self.close_price,
            volume=self.volume,
            quote_volume=self.quote_volume,
            number_of_trades=self.number_of_trades,
            taker_buy_base_volume=self.taker_buy_base_volume,
            taker_buy_quote_volume=self.taker_buy_quote_volume,
            first_trade_id=self.first_trade_id,
            last_trade_id=self.last_trade_id,
            is_closed=self.is_closed,
        )

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: str(v), datetime: lambda v: int(v.timestamp() * 1000)},
        populate_by_name=True,
    )


class KlineResponse(BaseModel):
    """
    K线数据响应模型

    用于API响应中的K线数据格式
    """

    open_time: int = Field(..., description="K线开始时间戳（毫秒）", alias="0")
    open_price: str = Field(..., description="开盘价", alias="1")
    high_price: str = Field(..., description="最高价", alias="2")
    low_price: str = Field(..., description="最低价", alias="3")
    close_price: str = Field(..., description="收盘价", alias="4")
    volume: str = Field(..., description="成交量", alias="5")
    close_time: int = Field(..., description="K线结束时间戳（毫秒）", alias="6")
    quote_volume: str = Field(..., description="成交额", alias="7")
    number_of_trades: int = Field(..., description="交易笔数", alias="8")
    taker_buy_base_volume: str = Field(..., description="主动买入成交量", alias="9")
    taker_buy_quote_volume: str = Field(..., description="主动买入成交额", alias="10")
    ignore: str = Field(default="0", description="忽略字段", alias="11")

    @field_validator("open_time", "close_time", mode="before")
    @classmethod
    def validate_timestamp(cls, v):
        if isinstance(v, datetime):
            return int(v.timestamp() * 1000)
        return v

    @field_validator("open_price", "high_price", "low_price", "close_price", mode="before")
    @classmethod
    def validate_price(cls, v):
        return str(v)

    @field_validator("volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume", mode="before")
    @classmethod
    def validate_volume(cls, v):
        return str(v)

    @field_validator("number_of_trades", mode="before")
    @classmethod
    def validate_trades(cls, v):
        return int(v)

    @classmethod
    def from_kline_data(cls, kline: KlineData) -> "KlineResponse":
        return cls(
            open_time=int(kline.open_time.timestamp() * 1000),
            open_price=str(kline.open_price),
            high_price=str(kline.high_price),
            low_price=str(kline.low_price),
            close_price=str(kline.close_price),
            volume=str(kline.volume),
            close_time=int(kline.close_time.timestamp() * 1000),
            quote_volume=str(kline.quote_volume),
            number_of_trades=kline.number_of_trades,
            taker_buy_base_volume=str(kline.taker_buy_base_volume),
            taker_buy_quote_volume=str(kline.taker_buy_quote_volume),
            ignore="0",
        )

    def to_list(self) -> list:
        """转换为列表格式（币安API响应格式）"""
        return [
            self.open_time,
            self.open_price,
            self.high_price,
            self.low_price,
            self.close_price,
            self.volume,
            self.close_time,
            self.quote_volume,
            self.number_of_trades,
            self.taker_buy_base_volume,
            self.taker_buy_quote_volume,
            self.ignore,
        ]

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: str(v)},
        populate_by_name=True,
        json_schema_extra={
            "example": [
                1655971200000,  # 开始时间
                "0.01086000",  # 开盘价
                "0.01086600",  # 最高价
                "0.01083600",  # 最低价
                "0.01083800",  # 收盘价
                "2290.53800000",  # 成交量
                1655974799999,  # 结束时间
                "24.85074442",  # 成交额
                2283,  # 交易笔数
                "1171.64000000",  # 主动买入成交量
                "12.71225884",  # 主动买入成交额
                "0",  # 忽略
            ]
        },
    )


class KlineWebSocketData(KlineValidatorMixin, BaseModel):
    """
    WebSocket K线数据（嵌套格式）

    用于解析币安WebSocket消息中k字段的数据。
    币安WS使用单字母字段名：t, T, o, c, h, l, v, n, q, V, Q, x
    """

    open_time: datetime = Field(..., description="K线开始时间", alias="t")
    close_time: datetime = Field(..., description="K线结束时间", alias="T")
    symbol: str = Field(..., description="交易对符号", alias="s")
    interval: str = Field(..., description="K线间隔", alias="i")

    open_price: Decimal = Field(..., ge=0, description="开盘价", alias="o")
    close_price: Decimal = Field(..., ge=0, description="收盘价", alias="c")
    high_price: Decimal = Field(..., ge=0, description="最高价", alias="h")
    low_price: Decimal = Field(..., ge=0, description="最低价", alias="l")

    volume: Decimal = Field(..., ge=0, description="成交量", alias="v")
    quote_volume: Decimal = Field(..., ge=0, description="成交额", alias="q")

    number_of_trades: int = Field(..., ge=0, description="交易笔数", alias="n")

    taker_buy_base_volume: Decimal = Field(default=Decimal("0"), ge=0, description="主动买入成交量", alias="V")
    taker_buy_quote_volume: Decimal = Field(default=Decimal("0"), ge=0, description="主动买入成交额", alias="Q")

    is_closed: bool = Field(..., description="K线是否已结束", alias="x")

    @field_validator("open_price", "close_price", "high_price", "low_price", mode="before")
    @classmethod
    def _validate_price_wrapper(cls, v):
        return cls._validate_price(v)

    @field_validator("volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume", mode="before")
    @classmethod
    def _validate_volume_wrapper(cls, v):
        return cls._validate_volume(v)

    @field_validator("open_time", "close_time", mode="before")
    @classmethod
    def _validate_datetime_wrapper(cls, v):
        return cls._validate_datetime(v)

    @model_validator(mode="after")
    def validate_all(self) -> "KlineWebSocketData":
        self._validate_ohlc_consistency(self)
        self._validate_time_consistency(self)
        return self

    def to_kline_data(self, full_symbol: str) -> KlineData:
        """转换为 KlineData 模型"""
        return KlineData(
            symbol=full_symbol,
            interval=self.interval,
            open_time=self.open_time,
            close_time=self.close_time,
            open_price=self.open_price,
            high_price=self.high_price,
            low_price=self.low_price,
            close_price=self.close_price,
            volume=self.volume,
            quote_volume=self.quote_volume,
            number_of_trades=self.number_of_trades,
            taker_buy_base_volume=self.taker_buy_base_volume,
            taker_buy_quote_volume=self.taker_buy_quote_volume,
            is_closed=self.is_closed,
        )

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: str(v), datetime: lambda v: int(v.timestamp() * 1000)},
        populate_by_name=True,
    )


class KlineWebSocket(BaseModel):
    """
    WebSocket K线数据模型

    用于处理币安WebSocket实时K线数据流。
    """

    event_type: Literal["kline"] = Field("kline", description="事件类型", alias="e")
    event_time: datetime = Field(..., description="事件时间", alias="E")
    symbol: str = Field(..., description="交易对符号", alias="s")
    kline: KlineWebSocketData = Field(..., description="K线数据", alias="k")

    @field_validator("event_time", mode="before")
    @classmethod
    def validate_event_time(cls, v):
        if isinstance(v, int):
            return datetime.fromtimestamp(v / 1000)
        return v

    @field_validator("symbol", mode="before")
    @classmethod
    def validate_symbol(cls, v):
        if isinstance(v, str) and not v.startswith("BINANCE:"):
            return f"BINANCE:{v.upper()}"
        return v

    def to_kline_data(self) -> KlineData:
        """转换为 KlineData 模型"""
        return self.kline.to_kline_data(self.symbol)

    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: str(v), datetime: lambda v: int(v.timestamp() * 1000)},
        populate_by_name=True,
    )


class KlineInterval:
    """K线间隔常量"""

    INTERVAL_1M = "1m"
    INTERVAL_3M = "3m"
    INTERVAL_5M = "5m"
    INTERVAL_15M = "15m"
    INTERVAL_30M = "30m"

    INTERVAL_1H = "1h"
    INTERVAL_2H = "2h"
    INTERVAL_4H = "4h"
    INTERVAL_6H = "6h"
    INTERVAL_8H = "8h"
    INTERVAL_12H = "12h"

    INTERVAL_1D = "1d"
    INTERVAL_3D = "3d"

    INTERVAL_1W = "1w"

    INTERVAL_1M_MONTH = "1M"

    @classmethod
    def get_all_intervals(cls) -> list[str]:
        return [
            cls.INTERVAL_1M, cls.INTERVAL_3M, cls.INTERVAL_5M,
            cls.INTERVAL_15M, cls.INTERVAL_30M,
            cls.INTERVAL_1H, cls.INTERVAL_2H, cls.INTERVAL_4H,
            cls.INTERVAL_6H, cls.INTERVAL_8H, cls.INTERVAL_12H,
            cls.INTERVAL_1D, cls.INTERVAL_3D,
            cls.INTERVAL_1W, cls.INTERVAL_1M_MONTH,
        ]

    @classmethod
    def get_minute_intervals(cls) -> list[str]:
        return [
            cls.INTERVAL_1M, cls.INTERVAL_3M, cls.INTERVAL_5M,
            cls.INTERVAL_15M, cls.INTERVAL_30M,
        ]

    @classmethod
    def get_hour_intervals(cls) -> list[str]:
        return [
            cls.INTERVAL_1H, cls.INTERVAL_2H, cls.INTERVAL_4H,
            cls.INTERVAL_6H, cls.INTERVAL_8H, cls.INTERVAL_12H,
        ]

    @classmethod
    def get_day_intervals(cls) -> list[str]:
        return [cls.INTERVAL_1D, cls.INTERVAL_3D]
