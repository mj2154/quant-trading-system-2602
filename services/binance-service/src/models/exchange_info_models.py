"""
交易所信息数据模型

严格遵循币安官方文档格式。

文档来源:
- 现货交易所信息: binance_spot_docs/01_REST API/General endpoints.md
- 期货交易所信息: binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/获取交易规则和交易对.md
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# 现货交易所信息
# =============================================================================


class BinanceSpotExchangeInfoRateLimitModel(BaseModel):
    """现货交易所信息 - 频率限制子模型

    文档来源: binance_spot_docs/01_REST API/General endpoints.md
    """

    interval: str = Field(description="限流间隔")
    interval_num: int = Field(alias="intervalNum", description="间隔数量")
    limit: int = Field(description="限制数量")
    rate_limit_type: str = Field(alias="rateLimitType", description="限流类型")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotExchangeInfoSymbolFilterModel(BaseModel):
    """现货交易所信息 - Symbol过滤器子模型（基类）

    文档来源: binance_spot_docs/01_REST API/General endpoints.md
    """

    filter_type: str = Field(alias="filterType", description="过滤器类型")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotExchangeInfoSymbolModel(BaseModel):
    """现货交易所信息 - 交易对子模型

    文档来源: binance_spot_docs/01_REST API/General endpoints.md
    """

    symbol: str = Field(description="交易对")
    status: str = Field(description="交易对状态")
    base_asset: str = Field(alias="baseAsset", description="基础资产")
    base_asset_precision: int = Field(alias="baseAssetPrecision", description="基础资产精度")
    quote_asset: str = Field(alias="quoteAsset", description="报价资产")
    quote_precision: int = Field(alias="quotePrecision", description="报价精度（已废弃）")
    quote_asset_precision: int = Field(
        alias="quoteAssetPrecision", description="报价资产精度"
    )
    base_commission_precision: int = Field(
        alias="baseCommissionPrecision", description="基础手续费精度"
    )
    quote_commission_precision: int = Field(
        alias="quoteCommissionPrecision", description="报价手续费精度"
    )
    order_types: list[str] = Field(alias="orderTypes", description="支持的订单类型")
    iceberg_allowed: bool = Field(alias="icebergAllowed", description="是否允许冰山单")
    oco_allowed: bool = Field(alias="ocoAllowed", description="是否允许OCO订单")
    oto_allowed: bool = Field(alias="otoAllowed", description="是否允许OTO订单")
    opo_allowed: bool = Field(alias="opoAllowed", description="是否允许OPO订单")
    quote_order_qty_market_allowed: bool = Field(
        alias="quoteOrderQtyMarketAllowed", description="是否允许quote订单数量市价单"
    )
    allow_trailing_stop: bool = Field(
        alias="allowTrailingStop", description="是否允许追踪止损"
    )
    cancel_replace_allowed: bool = Field(
        alias="cancelReplaceAllowed", description="是否允许取消替换"
    )
    amend_allowed: bool = Field(alias="amendAllowed", description="是否允许修改订单")
    peg_instructions_allowed: bool = Field(
        alias="pegInstructionsAllowed", description="是否允许挂钩指令"
    )
    is_spot_trading_allowed: bool = Field(
        alias="isSpotTradingAllowed", description="是否允许现货交易"
    )
    is_margin_trading_allowed: bool = Field(
        alias="isMarginTradingAllowed", description="是否允许杠杆交易"
    )
    filters: list[dict] = Field(description="过滤器列表")
    permissions: list[str] = Field(description="权限列表")
    permission_sets: list[list[str]] = Field(
        alias="permissionSets", description="权限集合列表"
    )
    default_self_trade_prevention_mode: str = Field(
        alias="defaultSelfTradePreventionMode", description="默认自成交预防模式"
    )
    allowed_self_trade_prevention_modes: list[str] = Field(
        alias="allowedSelfTradePreventionModes", description="允许的自成交预防模式列表"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotExchangeInfoSorModel(BaseModel):
    """现货交易所信息 - SOR子模型

    文档来源: binance_spot_docs/01_REST API/General endpoints.md
    """

    base_asset: str = Field(alias="baseAsset", description="基础资产")
    symbols: list[str] = Field(description="交易对列表")

    model_config = ConfigDict(populate_by_name=True)


class BinanceSpotExchangeInfoGetModel(BaseModel):
    """现货交易所信息 GET 响应模型

    接口: GET /api/v3/exchangeInfo
    文档来源: binance_spot_docs/01_REST API/General endpoints.md
    """

    timezone: str = Field(description="时区")
    server_time: int = Field(alias="serverTime", description="服务器时间")
    rate_limits: list[BinanceSpotExchangeInfoRateLimitModel] = Field(
        alias="rateLimits", description="频率限制列表"
    )
    exchange_filters: list[dict] = Field(
        alias="exchangeFilters", description="交易所过滤器列表"
    )
    symbols: list[BinanceSpotExchangeInfoSymbolModel] = Field(
        description="交易对列表"
    )
    sors: list[BinanceSpotExchangeInfoSorModel] = Field(
        default=[], description="SOR列表"
    )

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货交易所信息
# =============================================================================


class BinanceFuturesExchangeInfoRateLimitModel(BaseModel):
    """期货交易所信息 - 频率限制子模型

    文档来源: binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/获取交易规则和交易对.md
    """

    interval: str = Field(description="限流间隔")
    interval_num: int = Field(alias="intervalNum", description="间隔数量")
    limit: int = Field(description="限制数量")
    rate_limit_type: str = Field(alias="rateLimitType", description="限流类型")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesExchangeInfoAssetModel(BaseModel):
    """期货交易所信息 - 资产子模型

    文档来源: binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/获取交易规则和交易对.md
    """

    asset: str = Field(description="资产名称")
    margin_available: bool = Field(
        alias="marginAvailable", description="是否可用作保证金"
    )
    auto_asset_exchange: str | None = Field(
        alias="autoAssetExchange", description="自动兑换阈值"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesExchangeInfoSymbolFilterModel(BaseModel):
    """期货交易所信息 - Symbol过滤器子模型（基类）

    文档来源: binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/获取交易规则和交易对.md
    """

    filter_type: str = Field(alias="filterType", description="过滤器类型")

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesExchangeInfoSymbolModel(BaseModel):
    """期货交易所信息 - 交易对子模型

    文档来源: binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/获取交易规则和交易对.md
    """

    symbol: str = Field(description="交易对")
    pair: str = Field(description="交易对名称")
    contract_type: str = Field(alias="contractType", description="合约类型")
    delivery_date: int = Field(alias="deliveryDate", description="交割日期")
    onboard_date: int = Field(alias="onboardDate", description="上线日期")
    status: str = Field(description="交易对状态")
    maint_margin_percent: str = Field(
        alias="maintMarginPercent", description="维持保证金比例（已废弃）"
    )
    required_margin_percent: str = Field(
        alias="requiredMarginPercent", description="所需保证金比例（已废弃）"
    )
    base_asset: str = Field(alias="baseAsset", description="基础资产")
    quote_asset: str = Field(alias="quoteAsset", description="报价资产")
    margin_asset: str = Field(alias="marginAsset", description="保证金资产")
    price_precision: int = Field(
        alias="pricePrecision", description="价格精度（请勿用作tickSize）"
    )
    quantity_precision: int = Field(
        alias="quantityPrecision", description="数量精度（请勿用作stepSize）"
    )
    base_asset_precision: int = Field(alias="baseAssetPrecision", description="基础资产精度")
    quote_precision: int = Field(alias="quotePrecision", description="报价精度")
    underlying_type: str = Field(alias="underlyingType", description="底层资产类型")
    underlying_sub_type: list[str] = Field(
        alias="underlyingSubType", description="底层资产子类型"
    )
    settle_plan: int | None = Field(
        default=None, alias="settlePlan", description="结算计划（条件字段，仅标准永续合约有）"
    )
    trigger_protect: str = Field(
        alias="triggerProtect", description="触发保护阈值"
    )
    filters: list[dict] = Field(description="过滤器列表")
    order_type: list[str] | None = Field(
        default=None, alias="OrderType", description="订单类型列表（条件字段，仅标准合约有）"
    )
    time_in_force: list[str] = Field(
        alias="timeInForce", description="有效期限列表"
    )
    liquidation_fee: str = Field(
        alias="liquidationFee", description="强平手续费率"
    )
    market_take_bound: str = Field(
        alias="marketTakeBound", description="市场单最大价格偏离比例"
    )

    model_config = ConfigDict(populate_by_name=True)


class BinanceFuturesExchangeInfoGetModel(BaseModel):
    """期货交易所信息 GET 响应模型

    接口: GET /fapi/v1/exchangeInfo
    文档来源: binance_futures_docs/01_U本位合约/02_行情接口/03_REST API/获取交易规则和交易对.md
    """

    exchange_filters: list[dict] = Field(
        alias="exchangeFilters", description="交易所过滤器列表"
    )
    rate_limits: list[BinanceFuturesExchangeInfoRateLimitModel] = Field(
        alias="rateLimits", description="频率限制列表"
    )
    server_time: int = Field(alias="serverTime", description="服务器时间")
    assets: list[BinanceFuturesExchangeInfoAssetModel] = Field(description="资产列表")
    symbols: list[BinanceFuturesExchangeInfoSymbolModel] = Field(
        description="交易对列表"
    )
    timezone: str = Field(description="时区")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 市场类型枚举
# =============================================================================


class MarketType(str, Enum):
    """市场类型枚举"""

    SPOT = "SPOT"
    FUTURES = "FUTURES"


# =============================================================================
# 数据库存储模型
# =============================================================================


class ExchangeInfo:
    """交易所信息数据库模型

    用于存储到 exchange_info 表的模型。
    注意：这是一个普通类，不是 Pydantic 模型，因为数据库返回的是 dict。

    属性与 exchange_info 表字段一一对应。
    """

    def __init__(
        self,
        exchange: str,
        market_type: str,
        symbol: str,
        base_asset: str,
        quote_asset: str,
        status: str,
        base_asset_precision: int,
        quote_precision: int,
        quote_asset_precision: int,
        base_commission_precision: int,
        quote_commission_precision: int,
        filters: list[dict],
        order_types: list[str],
        permissions: list[str],
        iceberg_allowed: bool,
        oco_allowed: bool,
        oto_allowed: bool,
        opo_allowed: bool,
        quote_order_qty_market_allowed: bool,
        allow_trailing_stop: bool,
        cancel_replace_allowed: bool,
        amend_allowed: bool,
        peg_instructions_allowed: bool,
        is_spot_trading_allowed: bool,
        is_margin_trading_allowed: bool,
        permission_sets: list[list[str]],
        default_self_trade_prevention_mode: str,
        allowed_self_trade_prevention_modes: list[str],
        last_updated: datetime | None = None,
    ) -> None:
        self.exchange = exchange
        self.market_type = market_type
        self.symbol = symbol
        self.base_asset = base_asset
        self.quote_asset = quote_asset
        self.status = status
        self.base_asset_precision = base_asset_precision
        self.quote_precision = quote_precision
        self.quote_asset_precision = quote_asset_precision
        self.base_commission_precision = base_commission_precision
        self.quote_commission_precision = quote_commission_precision
        self.filters = filters
        self.order_types = order_types
        self.permissions = permissions
        self.iceberg_allowed = iceberg_allowed
        self.oco_allowed = oco_allowed
        self.oto_allowed = oto_allowed
        self.opo_allowed = opo_allowed
        self.quote_order_qty_market_allowed = quote_order_qty_market_allowed
        self.allow_trailing_stop = allow_trailing_stop
        self.cancel_replace_allowed = cancel_replace_allowed
        self.amend_allowed = amend_allowed
        self.peg_instructions_allowed = peg_instructions_allowed
        self.is_spot_trading_allowed = is_spot_trading_allowed
        self.is_margin_trading_allowed = is_margin_trading_allowed
        self.permission_sets = permission_sets
        self.default_self_trade_prevention_mode = default_self_trade_prevention_mode
        self.allowed_self_trade_prevention_modes = allowed_self_trade_prevention_modes
        self.last_updated = last_updated


# =============================================================================
# 现货交易对模型转换为数据库模型
# =============================================================================


def _spot_symbol_to_exchange_info(
    self: BinanceSpotExchangeInfoSymbolModel, exchange: str
) -> ExchangeInfo:
    """将现货交易对模型转换为数据库模型

    Args:
        self: 现货交易对模型
        exchange: 交易所名称

    Returns:
        ExchangeInfo 数据库模型
    """
    return ExchangeInfo(
        exchange=exchange,
        market_type=MarketType.SPOT.value,
        symbol=self.symbol,
        base_asset=self.base_asset,
        quote_asset=self.quote_asset,
        status=self.status,
        base_asset_precision=self.base_asset_precision,
        quote_precision=self.quote_precision,
        quote_asset_precision=self.quote_asset_precision,
        base_commission_precision=self.base_commission_precision,
        quote_commission_precision=self.quote_commission_precision,
        filters=self.filters,
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


# 添加方法到现货交易对模型
BinanceSpotExchangeInfoSymbolModel.to_exchange_info = lambda self, exchange="BINANCE": _spot_symbol_to_exchange_info(self, exchange)


# =============================================================================
# 期货交易对模型转换为数据库模型
# =============================================================================


def _futures_symbol_to_exchange_info(
    self: BinanceFuturesExchangeInfoSymbolModel, exchange: str
) -> ExchangeInfo:
    """将期货交易对模型转换为数据库模型

    Args:
        self: 期货交易对模型
        exchange: 交易所名称

    Returns:
        ExchangeInfo 数据库模型
    """
    return ExchangeInfo(
        exchange=exchange,
        market_type=MarketType.FUTURES.value,
        symbol=self.symbol,
        base_asset=self.base_asset,
        quote_asset=self.quote_asset,
        status=self.status,
        base_asset_precision=self.base_asset_precision,
        quote_precision=self.quote_precision,
        quote_asset_precision=self.quote_precision,  # 期货用 quote_precision
        base_commission_precision=0,  # 期货没有这个字段
        quote_commission_precision=0,  # 期货没有这个字段
        filters=self.filters,
        order_types=self.order_type or [],  # 期货用 order_type，None时使用空列表
        permissions=[],  # 期货没有这个字段
        iceberg_allowed=False,  # 期货没有这个字段
        oco_allowed=False,  # 期货没有这个字段
        oto_allowed=False,  # 期货没有这个字段
        opo_allowed=False,  # 期货没有这个字段
        quote_order_qty_market_allowed=False,  # 期货没有这个字段
        allow_trailing_stop=False,  # 期货没有这个字段
        cancel_replace_allowed=False,  # 期货没有这个字段
        amend_allowed=False,  # 期货没有这个字段
        peg_instructions_allowed=False,  # 期货没有这个字段
        is_spot_trading_allowed=False,  # 期货没有这个字段
        is_margin_trading_allowed=True,  # 期货是保证金交易
        permission_sets=[],  # 期货没有这个字段
        default_self_trade_prevention_mode="",  # 期货没有这个字段
        allowed_self_trade_prevention_modes=[],  # 期货没有这个字段
    )


# 添加方法到期货交易对模型
BinanceFuturesExchangeInfoSymbolModel.to_exchange_info = lambda self, exchange="BINANCE": _futures_symbol_to_exchange_info(self, exchange)
