"""
币安账户信息数据模型

严格遵循文档: docs/backend/design/09-binance-models.md

现货账户: GET /api/v3/account
期货账户: GET /fapi/v3/account
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .base import SnakeCaseModel


# =============================================================================
# 现货（SPOT）账户模型
# =============================================================================


class BinanceSpotAccountCommissionRateModel(BaseModel):
    """现货账户手续费率子模型

    文档来源: binance_spot_docs/01_REST API/Account Endpoints.md
    """

    maker: str = Field(description="Maker 手续费率")
    taker: str = Field(description="Taker 手续费率")
    buyer: str = Field(description="买方手续费率")
    seller: str = Field(description="卖方手续费率")


class BinanceSpotAccountBalanceModel(BaseModel):
    """现货账户余额子模型

    文档来源: binance_spot_docs/01_REST API/Account Endpoints.md
    """

    asset: str = Field(description="资产名称")
    free: str = Field(description="可用余额")
    locked: str = Field(description="锁定余额")


class BinanceSpotAccountGetModel(SnakeCaseModel):
    """现货账户信息 GET 响应模型

    接口: GET /api/v3/account
    文档来源: binance_spot_docs/01_REST API/Account Endpoints.md
    """

    maker_commission: int = Field(alias="makerCommission", description="Maker 手续费")
    taker_commission: int = Field(alias="takerCommission", description="Taker 手续费")
    buyer_commission: int = Field(alias="buyerCommission", description="买方手续费")
    seller_commission: int = Field(alias="sellerCommission", description="卖方手续费")
    commission_rates: BinanceSpotAccountCommissionRateModel = Field(
        alias="commissionRates", description="手续费率"
    )
    can_trade: bool = Field(alias="canTrade", description="是否可交易")
    can_withdraw: bool = Field(alias="canWithdraw", description="是否可提现")
    can_deposit: bool = Field(alias="canDeposit", description="是否可充值")
    brokered: bool = Field(description="是否经纪商")
    require_self_trade_prevention: bool = Field(
        alias="requireSelfTradePrevention", description="是否需要自成交预防"
    )
    prevent_sor: bool = Field(alias="preventSor", description="是否阻止 SOR")
    update_time: int = Field(alias="updateTime", description="最后更新时间")
    account_type: str = Field(alias="accountType", description="账户类型")
    balances: list[BinanceSpotAccountBalanceModel] = Field(
        description="账户余额列表"
    )
    permissions: list[str] = Field(description="账户权限列表")
    uid: int | None = Field(default=None, description="用户 ID（部分账户返回）")

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# 期货（FUTURES）账户模型
# =============================================================================


class BinanceFuturesAccountAssetModel(BaseModel):
    """期货账户资产子模型

    文档来源: binance_futures_docs/01_U本位合约/02_账户接口/03_REST API/账户信息V3(USER-DATA).md
    """

    asset: str = Field(description="资产名称")
    wallet_balance: Decimal = Field(alias="walletBalance", description="钱包余额")
    unrealized_profit: Decimal = Field(alias="unrealizedProfit", description="未实现盈亏")
    margin_balance: Decimal = Field(alias="marginBalance", description="保证金余额")
    maint_margin: Decimal = Field(alias="maintMargin", description="维持保证金")
    initial_margin: Decimal = Field(alias="initialMargin", description="总初始保证金")
    position_initial_margin: Decimal = Field(
        alias="positionInitialMargin", description="持仓初始保证金"
    )
    open_order_initial_margin: Decimal = Field(
        alias="openOrderInitialMargin", description="挂单初始保证金"
    )
    cross_wallet_balance: Decimal = Field(
        alias="crossWalletBalance", description="跨账户钱包余额"
    )
    cross_un_pnl: Decimal = Field(alias="crossUnPnl", description="跨账户未实现盈亏")
    available_balance: Decimal = Field(alias="availableBalance", description="可用余额")
    max_withdraw_amount: Decimal = Field(
        alias="maxWithdrawAmount", description="最大可转出数量"
    )
    update_time: int = Field(alias="updateTime", description="最后更新时间")


class BinanceFuturesAccountPositionModel(BaseModel):
    """期货账户持仓子模型

    文档来源: binance_futures_docs/01_U本位合约/02_账户接口/03_REST API/账户信息V3(USER-DATA).md
    """

    symbol: str = Field(description="交易对")
    position_side: str = Field(alias="positionSide", description="持仓方向")
    position_amt: Decimal = Field(alias="positionAmt", description="持仓数量")
    unrealized_profit: Decimal = Field(alias="unrealizedProfit", description="未实现盈亏")
    isolated_margin: Decimal = Field(alias="isolatedMargin", description="逐仓保证金")
    notional: Decimal = Field(description="名义价值")
    isolated_wallet: Decimal = Field(alias="isolatedWallet", description="逐仓钱包")
    initial_margin: Decimal = Field(alias="initialMargin", description="初始保证金")
    maint_margin: Decimal = Field(alias="maintMargin", description="维持保证金")
    update_time: int = Field(alias="updateTime", description="最后更新时间")


class BinanceFuturesAccountGetModel(SnakeCaseModel):
    """期货账户信息 GET 响应模型

    接口: GET /fapi/v3/account
    文档来源: binance_futures_docs/01_U本位合约/02_账户接口/03_REST API/账户信息V3(USER-DATA).md
    """

    total_initial_margin: Decimal = Field(
        alias="totalInitialMargin", description="总初始保证金"
    )
    total_maint_margin: Decimal = Field(
        alias="totalMaintMargin", description="总维持保证金"
    )
    total_wallet_balance: Decimal = Field(
        alias="totalWalletBalance", description="总钱包余额"
    )
    total_unrealized_profit: Decimal = Field(
        alias="totalUnrealizedProfit", description="总未实现盈亏"
    )
    total_margin_balance: Decimal = Field(
        alias="totalMarginBalance", description="总保证金余额"
    )
    total_position_initial_margin: Decimal = Field(
        alias="totalPositionInitialMargin", description="总持仓初始保证金"
    )
    total_open_order_initial_margin: Decimal = Field(
        alias="totalOpenOrderInitialMargin", description="总挂单初始保证金"
    )
    total_cross_wallet_balance: Decimal = Field(
        alias="totalCrossWalletBalance", description="总跨账户钱包余额"
    )
    total_cross_un_pnl: Decimal = Field(
        alias="totalCrossUnPnl", description="总跨账户未实现盈亏"
    )
    available_balance: Decimal = Field(
        alias="availableBalance", description="可用余额"
    )
    max_withdraw_amount: Decimal = Field(
        alias="maxWithdrawAmount", description="最大可转出数量"
    )
    assets: list[BinanceFuturesAccountAssetModel] = Field(description="资产列表")
    positions: list[BinanceFuturesAccountPositionModel] = Field(description="持仓列表")

    model_config = ConfigDict(populate_by_name=True)
