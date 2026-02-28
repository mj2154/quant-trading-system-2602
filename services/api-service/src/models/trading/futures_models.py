"""
期货特有数据模型

期货特有的数据模型，包括标记价格、资金费率、持仓量等。
K线数据使用统一的 KlineBar 模型。

作者: Claude Code
版本: v2.0.0
"""

from pydantic import BaseModel, ConfigDict


class MarkPriceData(BaseModel):
    """标记价格数据

    包含期货特有的标记价格、指数价格和资金费率信息。
    用于风险管理和平仓价格计算。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore", use_enum_values=True)

    symbol: str
    mark_price: float
    index_price: float
    last_funding_rate: float
    next_funding_time: int


class FundingRateData(BaseModel):
    """资金费率数据

    用于表示期货资金费率信息，包括当前费率和结算时间。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore", use_enum_values=True)

    symbol: str
    funding_rate: float
    funding_time: int


class OpenInterestData(BaseModel):
    """持仓量数据

    用于表示期货持仓量信息，包括总持仓量和持仓量价值。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore", use_enum_values=True)

    symbol: str
    open_interest: float
    open_interest_value: float


class FuturesSymbolInfo(BaseModel):
    """期货交易对信息

    扩展了基础的 SymbolInfo，添加了期货特有的合约类型、保证金等信息。
    用于交易对查询和风险控制。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore", use_enum_values=True)

    # 基础信息
    exchange: str = "BINANCE"
    symbol: str
    base_asset: str
    quote_asset: str
    status: str

    # 期货特有字段
    contract_type: str  # "PERPETUAL" 表示永续合约
    delivery_date: int | None = None  # 交割日期 (永续合约为 None)
    listing_date: int  # 上市日期 (毫秒)

    # 交易规则
    initial_margin: float  # 初始保证金
    maintenance_margin: float  # 维持保证金
    price_tick: float  # 价格最小变动单位
    min_qty: float  # 最小下单量
    max_qty: float  # 最大下单量
    max_notional_value: float  # 最大名义价值

    # 手续费
    liquidation_fee: float  # 强平手续费率
    maker_commission: float  # 挂单手续费
    taker_commission: float  # 吃单手续费


class PremiumIndexData(BaseModel):
    """期货溢价指数数据"""

    symbol: str  # 交易对
    event_time: int  # 事件时间
    mark_price: float  # 标记价格
    index_price: float  # 指数价格
    mark_price_change: float  # 标记价格变化
    estimated_settle_price: float  # 预估结算价
    time_to_funding: int  # 距离下次资金费率时间


class OpenInterestStatsData(BaseModel):
    """期货未平仓量统计数据"""

    symbol: str  # 交易对
    event_time: int  # 事件时间
    sum_open_interest: float  # 总未平仓量
    sum_open_interest_value: float  # 总未平仓量价值
    count: int  # 统计数量


# 期货特有的订阅类型
FUTURES_SUBSCRIPTION_TYPES = [
    "kline",  # K 线数据
    "ticker",  # 报价数据
    "mark_price",  # 标记价格
    "funding_rate",  # 资金费率
    "open_interest",  # 持仓量
]


# 期货特有的分辨率
FUTURES_RESOLUTIONS = [
    "1",  # 1 分钟
    "3",  # 3 分钟
    "5",  # 5 分钟
    "15",  # 15 分钟
    "30",  # 30 分钟
    "60",  # 1 小时
    "120",  # 2 小时
    "240",  # 4 小时
    "360",  # 6 小时
    "480",  # 8 小时
    "720",  # 12 小时
    "D",  # 1 天
    "3D",  # 3 天
    "W",  # 1 周
    "M",  # 1 月
]
