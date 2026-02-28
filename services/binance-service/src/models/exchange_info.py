"""
交易所信息数据模型

基于币安API的exchangeInfo响应数据模型，支持现货和U本位永续合约。
用于解析和验证交易所交易对规则信息。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class PriceFilter(BaseModel):
    """价格过滤器

    定义下单价格的最小值、最大值和步长。
    """

    min_price: str = Field(..., description="最小价格")
    max_price: str = Field(..., description="最大价格")
    tick_size: str = Field(..., description="价格步长")

    @property
    def min_price_decimal(self) -> Decimal:
        """返回最小价格的Decimal表示"""
        return Decimal(self.min_price)

    @property
    def max_price_decimal(self) -> Decimal:
        """返回最大价格的Decimal表示"""
        return Decimal(self.max_price)

    @property
    def tick_size_decimal(self) -> Decimal:
        """返回价格步长的Decimal表示"""
        return Decimal(self.tick_size)


class LotSizeFilter(BaseModel):
    """数量过滤器

    定义下单数量的最小值、最大值和步长。
    """

    min_qty: str = Field(..., description="最小数量")
    max_qty: str = Field(..., description="最大数量")
    step_size: str = Field(..., description="数量步长")

    @property
    def min_qty_decimal(self) -> Decimal:
        """返回最小数量的Decimal表示"""
        return Decimal(self.min_qty)

    @property
    def max_qty_decimal(self) -> Decimal:
        """返回最大数量的Decimal表示"""
        return Decimal(self.max_qty)

    @property
    def step_size_decimal(self) -> Decimal:
        """返回数量步长的Decimal表示"""
        return Decimal(self.step_size)


class MinNotionalFilter(BaseModel):
    """最小名义价值过滤器

    定义下单的最小名义价值要求。
    """

    min_notional: str = Field(..., description="最小名义价值")
    apply_to_market: Optional[bool] = Field(None, description="是否适用于市价单")
    avg_price_mins: Optional[int] = Field(None, description="平均价格计算分钟数")

    @property
    def min_notional_decimal(self) -> Decimal:
        """返回最小名义价值的Decimal表示"""
        return Decimal(self.min_notional)


class ExchangeInfoSymbolFilter(BaseModel):
    """交易所信息过滤器

    币安API返回的过滤器类型。
    支持15+种过滤器类型，这里定义常见的几种。
    """

    price_filter: Optional[PriceFilter] = Field(None, alias="PRICE_FILTER")
    lot_size: Optional[LotSizeFilter] = Field(None, alias="LOT_SIZE")
    min_notional: Optional[MinNotionalFilter] = Field(None, alias="MIN_NOTIONAL")
    market_lot_size: Optional[LotSizeFilter] = Field(None, alias="MARKET_LOT_SIZE")
    percent_price: Optional[dict] = Field(None, alias="PERCENT_PRICE")
    percent_price_by_side: Optional[dict] = Field(None, alias="PERCENT_PRICE_BY_SIDE")
    iceberg_parts: Optional[dict] = Field(None, alias="ICEBERG_PARTS")
    trailing_delta: Optional[dict] = Field(None, alias="TRAILING_DELTA")
    delta_position: Optional[dict] = Field(None, alias="DELTA_POSITION")
    price_protect: Optional[dict] = Field(None, alias="PRICE_PROTECT")

    class Config:
        populate_by_name = True


class ExchangeInfoSymbol(BaseModel):
    """单个交易对信息

    来自币安exchangeInfo API的symbol对象。
    字段严格对应币安API返回的字段。
    """

    # 基本信息
    symbol: str = Field(default="", description="symbol")
    status: str = Field(default="UNKNOWN", description="status")
    base_asset: str = Field(default="", description="baseAsset")
    quote_asset: str = Field(default="", description="quoteAsset")

    # 精度信息（基于币安API字段）
    base_asset_precision: int = Field(default=8, ge=0, description="baseAssetPrecision")
    quote_precision: int = Field(default=8, ge=0, description="quotePrecision")
    quote_asset_precision: int = Field(
        default=8, ge=0, description="quoteAssetPrecision"
    )
    base_commission_precision: int = Field(
        default=8, ge=0, description="baseCommissionPrecision"
    )
    quote_commission_precision: int = Field(
        default=8, ge=0, description="quoteCommissionPrecision"
    )

    # 交易选项
    order_types: list[str] = Field(default_factory=list, description="orderTypes")
    permissions: list[str] = Field(default_factory=list, description="permissions")

    # 过滤器
    filters: list[dict] = Field(default_factory=list, description="filters")

    # 特殊选项（基于币安API字段）
    iceberg_allowed: bool = Field(default=False, description="icebergAllowed")
    oco_allowed: bool = Field(default=False, description="ocoAllowed")
    oto_allowed: bool = Field(default=False, description="otoAllowed")
    opo_allowed: bool = Field(default=False, description="opoAllowed")
    quote_order_qty_market_allowed: bool = Field(
        default=False, description="quoteOrderQtyMarketAllowed"
    )
    allow_trailing_stop: bool = Field(default=False, description="allowTrailingStop")
    cancel_replace_allowed: bool = Field(
        default=False, description="cancelReplaceAllowed"
    )
    amend_allowed: bool = Field(default=False, description="amendAllowed")
    peg_instructions_allowed: bool = Field(
        default=False, description="pegInstructionsAllowed"
    )

    # 交易权限（基于币安API字段）
    is_spot_trading_allowed: bool = Field(
        default=True, description="isSpotTradingAllowed"
    )
    is_margin_trading_allowed: bool = Field(
        default=False, description="isMarginTradingAllowed"
    )

    # 权限管理（基于币安API字段）
    permission_sets: list[list[str]] = Field(
        default_factory=list, description="permissionSets"
    )

    # 自成交防护（基于币安API字段）
    default_self_trade_prevention_mode: str = Field(
        default="NONE", description="defaultSelfTradePreventionMode"
    )
    allowed_self_trade_prevention_modes: list[str] = Field(
        default_factory=list, description="allowedSelfTradePreventionModes"
    )

    # 期货特有字段（可选）
    contract_type: Optional[str] = Field(None, description="contractType")
    delivery_date: Optional[int] = Field(None, description="deliveryDate")
    publish_time: Optional[int] = Field(None, description="publishTime")
    delivery_time: Optional[int] = Field(None, description="deliveryTime")
    onboard_date: Optional[int] = Field(None, description="onboardDate")
    maint_margin_percent: Optional[str] = Field(None, description="maintMarginPercent")
    required_margin_percent: Optional[str] = Field(
        None, description="requiredMarginPercent"
    )
    price_tick_scale: Optional[int] = Field(None, description="priceTickScale")
    quantity_step_scale: Optional[int] = Field(None, description="quantityStepScale")
    max_move_order_limit: Optional[int] = Field(None, description="maxMoveOrderLimit")

    @field_validator(
        "base_asset_precision",
        "quote_precision",
        "quote_asset_precision",
        "base_commission_precision",
        "quote_commission_precision",
        mode="before",
    )
    @classmethod
    def validate_precision(cls, v):
        """验证并转换精度字段"""
        if isinstance(v, str):
            return int(v)
        return v

    @field_validator("filters", mode="before")
    @classmethod
    def validate_filters(cls, v):
        """验证并转换过滤器为字典列表"""
        if v is None:
            return []
        if isinstance(v, list):
            return [dict(item) for item in v]
        return v

    def get_filter(self, filter_type: str) -> Optional[dict]:
        """获取指定类型的过滤器"""
        for f in self.filters:
            if f.get("filterType") == filter_type:
                return f
        return None

    def get_price_filter(self) -> Optional[PriceFilter]:
        """获取价格过滤器"""
        filter_dict = self.get_filter("PRICE_FILTER")
        if filter_dict:
            return PriceFilter(**filter_dict)
        return None

    def get_lot_size_filter(self) -> Optional[LotSizeFilter]:
        """获取数量过滤器"""
        filter_dict = self.get_filter("LOT_SIZE")
        if filter_dict:
            return LotSizeFilter(**filter_dict)
        return None

    def to_exchange_info(self, exchange: str, market_type: str) -> "ExchangeInfo":
        """转换为ExchangeInfo模型用于数据库存储"""
        return ExchangeInfo(
            exchange=exchange,
            market_type=market_type,
            symbol=self.symbol,
            base_asset=self.base_asset,
            quote_asset=self.quote_asset,
            status=self.status,
            base_asset_precision=self.base_asset_precision,
            quote_precision=self.quote_precision,
            quote_asset_precision=self.quote_asset_precision,
            base_commission_precision=self.base_commission_precision,
            quote_commission_precision=self.quote_commission_precision,
            filters={f["filterType"]: f for f in self.filters},
            order_types=self.order_types,
            permissions=self.permissions,
            iceberg_allowed=self.iceberg_allowed,
            oco_allowed=self.oco_allowed,
            oto_allowed=self.oto_allowed,
            opo_allowed=self.opo_allowed,
            quote_order_qty_market_allowed=self.quote_order_qty_market_allowed,
            allow_trailing_stop=self.allow_trailing_stop,
            cancel_replace_allowed=self.cancel_replace_allowed,
            amend_allowed=self.amend_allowed,
            peg_instructions_allowed=self.peg_instructions_allowed,
            is_spot_trading_allowed=self.is_spot_trading_allowed,
            is_margin_trading_allowed=self.is_margin_trading_allowed,
            permission_sets=self.permission_sets,
            default_self_trade_prevention_mode=self.default_self_trade_prevention_mode,
            allowed_self_trade_prevention_modes=self.allowed_self_trade_prevention_modes,
        )


class ExchangeInfoResponse(BaseModel):
    """交易所信息响应

    来自币安exchangeInfo API的根响应对象。
    """

    timezone: str = Field(default="UTC", description="服务器时区")
    server_time: int = Field(default=0, description="服务器时间戳（毫秒）")
    symbols: list[ExchangeInfoSymbol] = Field(
        default_factory=list, description="交易对信息列表"
    )

    @field_validator("server_time", mode="before")
    @classmethod
    def validate_server_time(cls, v):
        """验证时间戳"""
        if isinstance(v, datetime):
            return int(v.timestamp() * 1000)
        return v


class ExchangeInfo(BaseModel):
    """交易所信息模型

    用于数据库存储的交易所信息模型。
    与数据库表 exchange_info 字段对应（严格符合币安API字段）。
    """

    # 基本信息
    exchange: str = Field(default="BINANCE", description="exchange")
    market_type: str = Field(..., description="market_type")
    symbol: str = Field(default="", description="symbol")
    base_asset: str = Field(default="", description="base_asset")
    quote_asset: str = Field(default="", description="quote_asset")
    status: str = Field(default="TRADING", description="status")

    # 精度信息（基于币安API字段）
    base_asset_precision: int = Field(
        default=8, ge=0, description="base_asset_precision"
    )
    quote_precision: int = Field(default=8, ge=0, description="quote_precision")
    quote_asset_precision: int = Field(
        default=8, ge=0, description="quote_asset_precision"
    )
    base_commission_precision: int = Field(
        default=8, ge=0, description="base_commission_precision"
    )
    quote_commission_precision: int = Field(
        default=8, ge=0, description="quote_commission_precision"
    )

    # 交易规则过滤器
    filters: dict = Field(default_factory=dict, description="filters")

    # 交易选项
    order_types: list[str] = Field(default_factory=list, description="order_types")
    permissions: list[str] = Field(default_factory=list, description="permissions")

    # 特殊选项（基于币安API字段）
    iceberg_allowed: bool = Field(default=False, description="iceberg_allowed")
    oco_allowed: bool = Field(default=False, description="oco_allowed")
    oto_allowed: bool = Field(default=False, description="oto_allowed")
    opo_allowed: bool = Field(default=False, description="opo_allowed")
    quote_order_qty_market_allowed: bool = Field(
        default=False, description="quote_order_qty_market_allowed"
    )
    allow_trailing_stop: bool = Field(default=False, description="allow_trailing_stop")
    cancel_replace_allowed: bool = Field(
        default=False, description="cancel_replace_allowed"
    )
    amend_allowed: bool = Field(default=False, description="amend_allowed")
    peg_instructions_allowed: bool = Field(
        default=False, description="peg_instructions_allowed"
    )

    # 交易权限（基于币安API字段）
    is_spot_trading_allowed: bool = Field(
        default=True, description="is_spot_trading_allowed"
    )
    is_margin_trading_allowed: bool = Field(
        default=False, description="is_margin_trading_allowed"
    )

    # 权限管理（基于币安API字段）
    permission_sets: list[list[str]] = Field(
        default_factory=list, description="permission_sets"
    )

    # 自成交防护（基于币安API字段）
    default_self_trade_prevention_mode: str = Field(
        default="NONE", description="default_self_trade_prevention_mode"
    )
    allowed_self_trade_prevention_modes: list[str] = Field(
        default_factory=list, description="allowed_self_trade_prevention_modes"
    )

    # 更新时间
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="last_updated"
    )

    @property
    def full_symbol(self) -> str:
        """获取完整交易对名称

        Returns:
            格式: BINANCE:BTCUSDT 或 BINANCE:BTCUSDT.PERP
        """
        suffix = ".PERP" if self.market_type == "FUTURES" else ""
        return f"{self.exchange}:{self.symbol}{suffix}"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class MarketType:
    """市场类型常量"""

    SPOT = "SPOT"
    FUTURES = "FUTURES"


class ExchangeInfoStatus:
    """交易所状态常量"""

    TRADING = "TRADING"
    HALT = "HALT"
    BREAK = "BREAK"
