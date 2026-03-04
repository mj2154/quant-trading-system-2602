"""
WebSocket账户信息模型

用于私有WebSocket API的账户信息数据结构。
期货账户信息V2和现货账户信息模型。
使用camelCase与币安API保持一致。
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

# =============================================================================
# 期货账户信息模型
# =============================================================================


class FuturesAssetV2(BaseModel):
    """期货账户资产V2

    WebSocket API v2/account.status 返回的资产信息。

    字段说明：
    - account_alias: 账户别名
    - asset: 资产名称
    - balance: 钱包余额 (account.balance响应)
    - wallet_balance: 钱包余额 (v2/account.status响应)
    - unrealized_profit: 未实现盈亏
    - margin_balance: 保证金余额
    - maint_margin: 维持保证金
    - initial_margin: 起始保证金
    - position_initial_margin: 持仓起始保证金
    - open_order_initial_margin: 挂单起始保证金
    - cross_wallet_balance: 全仓钱包余额
    - cross_un_pnl: 全仓未实现盈亏
    - available_balance: 可用余额
    - max_withdraw_amount: 最大可转出金额
    - margin_available: 是否可用作保证金（多资产模式）
    - update_time: 更新时间
    """

    # account.balance 响应字段
    account_alias: Optional[str] = Field(default=None, alias="accountAlias")
    asset: str = Field(..., alias="asset")
    balance: Optional[str] = Field(default="0", alias="balance")

    # v2/account.status 响应字段
    wallet_balance: Optional[str] = Field(default="0", alias="walletBalance")
    unrealized_profit: str = Field(default="0", alias="unrealizedProfit")
    margin_balance: str = Field(default="0", alias="marginBalance")
    maint_margin: str = Field(default="0", alias="maintMargin")
    initial_margin: str = Field(default="0", alias="initialMargin")
    position_initial_margin: str = Field(default="0", alias="positionInitialMargin")
    open_order_initial_margin: str = Field(default="0", alias="openOrderInitialMargin")
    cross_wallet_balance: str = Field(default="0", alias="crossWalletBalance")
    cross_un_pnl: str = Field(default="0", alias="crossUnPnl")
    available_balance: str = Field(default="0", alias="availableBalance")
    max_withdraw_amount: str = Field(default="0", alias="maxWithdrawAmount")
    margin_available: Optional[bool] = Field(default=None, alias="marginAvailable")
    update_time: int = Field(default=0, alias="updateTime")

    model_config = {"populate_by_name": True}


class FuturesPositionV2(BaseModel):
    """期货持仓V2

    WebSocket API v2/account.status 返回的持仓信息。

    字段说明：
    - symbol: 交易对
    - position_side: 持仓方向（LONG/SHORT/BOTH）
    - position_amt: 持仓数量
    - unrealized_profit: 未实现盈亏
    - isolated_margin: 逐仓保证金
    - notional: 名义价值
    - isolated_wallet: 逐仓钱包余额
    - initial_margin: 起始保证金
    - maint_margin: 维持保证金
    - update_time: 更新时间
    """

    symbol: str = Field(..., alias="symbol")
    position_side: str = Field(default="BOTH", alias="positionSide")
    position_amt: str = Field(default="0", alias="positionAmt")
    unrealized_profit: str = Field(default="0", alias="unrealizedProfit")
    isolated_margin: str = Field(default="0", alias="isolatedMargin")
    notional: str = Field(default="0", alias="notional")
    isolated_wallet: str = Field(default="0", alias="isolatedWallet")
    initial_margin: str = Field(default="0", alias="initialMargin")
    maint_margin: str = Field(default="0", alias="maintMargin")
    update_time: int = Field(default=0, alias="updateTime")

    model_config = {"populate_by_name": True}


class FuturesAccountInfoV2WS(BaseModel):
    """期货账户信息V2 (WebSocket API)

    通过WebSocket API的v2/account.status接口返回。
    包含完整的账户信息和持仓数据。

    字段说明：
    - total_initial_margin: 总起始保证金
    - total_maint_margin: 总维持保证金
    - total_wallet_balance: 总钱包余额
    - total_unrealized_profit: 总未实现盈亏
    - total_margin_balance: 总保证金余额
    - total_position_initial_margin: 持仓起始保证金总额
    - total_open_order_initial_margin: 挂单起始保证金总额
    - total_cross_wallet_balance: 全仓钱包余额
    - total_cross_un_pnl: 全仓未实现盈亏
    - available_balance: 可用余额
    - max_withdraw_amount: 最大可转出金额
    - assets: 资产列表
    - positions: 持仓列表
    """

    total_initial_margin: str = Field(default="0", alias="totalInitialMargin")
    total_maint_margin: str = Field(default="0", alias="totalMaintMargin")
    total_wallet_balance: str = Field(default="0", alias="totalWalletBalance")
    total_unrealized_profit: str = Field(default="0", alias="totalUnrealizedProfit")
    total_margin_balance: str = Field(default="0", alias="totalMarginBalance")
    total_position_initial_margin: str = Field(default="0", alias="totalPositionInitialMargin")
    total_open_order_initial_margin: str = Field(default="0", alias="totalOpenOrderInitialMargin")
    total_cross_wallet_balance: str = Field(default="0", alias="totalCrossWalletBalance")
    total_cross_un_pnl: str = Field(default="0", alias="totalCrossUnPnl")
    available_balance: str = Field(default="0", alias="availableBalance")
    max_withdraw_amount: str = Field(default="0", alias="maxWithdrawAmount")
    assets: list[FuturesAssetV2] = Field(default_factory=list, alias="assets")
    positions: list[FuturesPositionV2] = Field(default_factory=list, alias="positions")

    model_config = {"populate_by_name": True}


class FuturesAsset(BaseModel):
    """期货账户资产

    字段说明：
    - asset: 资产名称
    - margin_balance: 保证金余额
    - wallet_balance: 钱包余额
    - available_balance: 可用余额
    - initial_margin: 起始保证金
    - maintenance_margin: 维持保证金
    - unrealized_pnl: 未实现盈亏
    """

    asset: str = Field(..., alias="a")
    margin_balance: str = Field(..., alias="mb")
    wallet_balance: str = Field(..., alias="wb")
    available_balance: str = Field(..., alias="ab")
    initial_margin: str = Field(..., alias="im")
    maintenance_margin: str = Field(..., alias="mm")
    unrealized_pnl: str = Field(..., alias="up")

    model_config = {"populate_by_name": True}


class FuturesPosition(BaseModel):
    """期货持仓

    字段说明：
    - symbol: 交易对
    - position_side: 持仓方向（LONG/SHORT/BOTH）
    - position_side_value: 持仓方向数值（1=long, 2=short, 3=both）
    - quantity: 持仓数量
    - entry_price: 开仓价格
    - mark_price: 标记价格
    - unrealized_pnl: 未实现盈亏
    - margin_balance: 保证金余额
    - isolated_margin: 逐仓保证金
    - is_auto_add_margin: 是否自动追加保证金
    """

    symbol: str = Field(..., alias="s")
    position_side: str = Field(..., alias="ps")
    position_side_value: int = Field(..., alias="psb")
    quantity: str = Field(..., alias="pa")
    entry_price: str = Field(..., alias="ep")
    mark_price: str = Field(..., alias="mp")
    unrealized_pnl: str = Field(..., alias="up")
    margin_balance: str = Field(..., alias="mb")
    isolated_margin: Optional[str] = Field(default=None, alias="im")
    is_auto_add_margin: bool = Field(..., alias="aaf")

    model_config = {"populate_by_name": True}


class FuturesAccountInfoV2(BaseModel):
    """期货账户信息V2

    通过WebSocket API的account.getBalance接口返回。
    包含完整的账户信息和持仓数据。

    字段说明：
    - fee_broker_bnb: 手续费BNB结算 Broker
    - can_deposit: 是否可以充值
    - can_trade: 是否可以交易
    - can_withdraw: 是否可以提现
    - fee_bnb: 手续费BNB抵扣
    - total_balance: 总余额
    - total_margin_balance: 总保证金余额
    - total_available_balance: 总可用余额
    - total_initial_margin: 总起始保证金
    - total_maintenance_margin: 总维持保证金
    - total_unrealized_pnl: 总未实现盈亏
    - assets: 资产列表
    - positions: 持仓列表
    """

    fee_broker_bnb: str = Field(..., alias="fb")
    can_deposit: bool = Field(..., alias="d")
    can_trade: bool = Field(..., alias="t")
    can_withdraw: bool = Field(..., alias="w")
    fee_bnb: str = Field(..., alias="f")
    total_balance: str = Field(..., alias="tb")
    total_margin_balance: str = Field(..., alias="tmb")
    total_available_balance: str = Field(..., alias="tab")
    total_initial_margin: str = Field(..., alias="tim")
    total_maintenance_margin: str = Field(..., alias="tmm")
    total_unrealized_pnl: str = Field(..., alias="tup")
    assets: list[FuturesAsset] = Field(default_factory=list, alias="B")
    positions: list[FuturesPosition] = Field(default_factory=list, alias="P")

    model_config = {"populate_by_name": True}


# =============================================================================
# 现货账户信息模型
# =============================================================================


class CommissionRates(BaseModel):
    """现货手续费率

    字段说明：
    - maker_commission: 挂单手续费率
    - taker_commission: 吃单手续费率
    """

    maker_commission: str = Field(..., alias="makerCommission")
    taker_commission: str = Field(..., alias="takerCommission")

    model_config = {"populate_by_name": True}


class SpotBalance(BaseModel):
    """现货余额

    字段说明：
    - asset: 资产名称
    - free: 可用余额
    - locked: 锁定余额
    """

    asset: str = Field(..., alias="a")
    free: str = Field(..., alias="f")
    locked: str = Field(..., alias="l")

    model_config = {"populate_by_name": True}


class SpotAccountInfo(BaseModel):
    """现货账户信息

    通过WebSocket API的account.getInfo接口返回。
    包含完整的账户信息和余额数据。

    字段说明：
    - maker_commission: 挂单手续费率（千分比）
    - taker_commission: 吃单手续费率（千分比）
    - buyer_commission: 买家手续费率（千分比）
    - seller_commission: 卖家手续费率（千分比）
    - can_trade: 是否可以交易
    - can_withdraw: 是否可以提现
    - can_deposit: 是否可以充值
    - update_time: 更新时间（毫秒时间戳）
    - account_type: 账户类型
    - balances: 余额列表（解析后的对象）
    - balances_raw: 余额列表（原始数据）
    - commission_rates: 手续费率
    """

    maker_commission: int = Field(..., alias="makerCommission")
    taker_commission: int = Field(..., alias="takerCommission")
    buyer_commission: int = Field(..., alias="buyerCommission")
    seller_commission: int = Field(..., alias="sellerCommission")
    can_trade: bool = Field(..., alias="canTrade")
    can_withdraw: bool = Field(..., alias="canWithdraw")
    can_deposit: bool = Field(..., alias="canDeposit")
    update_time: int = Field(..., alias="updateTime")
    account_type: str = Field(..., alias="accountType")
    balances: list[SpotBalance] = Field(default_factory=list, alias="balances")
    balances_raw: list[dict[str, Any]] = Field(default_factory=list, alias="balances")
    commission_rates: Optional[CommissionRates] = Field(
        default=None, alias="commissionRates"
    )

    model_config = {"populate_by_name": True}


# =============================================================================
# 辅助函数
# =============================================================================


def parse_futures_account_info_v2(data: dict[str, Any]) -> FuturesAccountInfoV2:
    """解析期货账户信息V2

    Args:
        data: 原始API响应数据

    Returns:
        FuturesAccountInfoV2对象
    """
    return FuturesAccountInfoV2.model_validate(data)


def parse_spot_account_info(data: dict[str, Any]) -> SpotAccountInfo:
    """解析现货账户信息

    Args:
        data: 原始API响应数据

    Returns:
        SpotAccountInfo对象
    """
    return SpotAccountInfo.model_validate(data)
