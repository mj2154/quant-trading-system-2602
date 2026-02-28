"""
币安期货账户信息数据模型

定义期货账户信息和持仓的Pydantic模型。

对应API: GET /fapi/v3/account
API文档: https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Account-Information-V3
"""

from typing import Optional

from pydantic import BaseModel, Field


class FuturesAsset(BaseModel):
    """期货资产信息

    账户中特定资产的余额和保证金详情。
    对应 /fapi/v3/account 响应中的 assets 数组元素。
    """

    asset: str = Field(..., description="资产名称，如 USDT, BUSD, BTC")
    wallet_balance: Optional[str] = Field(None, alias="walletBalance", description="余额")
    unrealized_profit: Optional[str] = Field(None, alias="unrealizedProfit", description="未实现盈亏")
    margin_balance: Optional[str] = Field(None, alias="marginBalance", description="保证金余额")
    maint_margin: Optional[str] = Field(None, alias="maintMargin", description="维持保证金")
    initial_margin: Optional[str] = Field(None, alias="initialMargin", description="当前所需起始保证金")
    position_initial_margin: Optional[str] = Field(
        None, alias="positionInitialMargin", description="持仓所需起始保证金(基于最新标记价格)"
    )
    open_order_initial_margin: Optional[str] = Field(
        None, alias="openOrderInitialMargin", description="当前挂单所需起始保证金(基于最新标记价格)"
    )
    cross_wallet_balance: Optional[str] = Field(
        None, alias="crossWalletBalance", description="全仓账户余额"
    )
    cross_unrealized_profit: Optional[str] = Field(
        None, alias="crossUnPnl", description="全仓持仓未实现盈亏"
    )
    available_balance: Optional[str] = Field(
        None, alias="availableBalance", description="可用余额"
    )
    max_withdraw_amount: Optional[str] = Field(
        None, alias="maxWithdrawAmount", description="最大可转出余额"
    )
    update_time: Optional[int] = Field(None, alias="updateTime", description="更新时间")

    model_config = {
        "populate_by_name": True,
    }


class FuturesPosition(BaseModel):
    """期货持仓信息

    对应 /fapi/v3/account 响应中的 positions 数组元素。
    字段名严格与币安官方文档一致: https://binance-docs.github.io/apidocs/futures/cn/

    注意：根据用户持仓模式展示持仓方向，
    - 单向模式：只返回 BOTH 持仓
    - 双向模式：只返回 LONG 和 SHORT 持仓
    """

    # 核心字段 (与币安API完全一致)
    symbol: str = Field(..., description="交易对符号，如 BTCUSDT")
    position_side: Optional[str] = Field(None, alias="positionSide", description="持仓方向: BOTH, LONG, SHORT")
    position_amt: Optional[str] = Field(None, alias="positionAmt", description="持仓数量")
    unrealized_profit: Optional[str] = Field(None, alias="unrealizedProfit", description="持仓未实现盈亏")

    # V3版本字段
    isolated_margin: Optional[str] = Field(None, alias="isolatedMargin", description="逐仓保证金")
    notional: Optional[str] = Field(None, alias="notional", description="名义价值")
    isolated_wallet: Optional[str] = Field(None, alias="isolatedWallet", description="逐仓钱包余额")
    initial_margin: Optional[str] = Field(None, alias="initialMargin", description="持仓所需起始保证金(基于最新标记价格)")
    maint_margin: Optional[str] = Field(None, alias="maintMargin", description="维持保证金")
    update_time: Optional[int] = Field(None, alias="updateTime", description="更新时间")

    model_config = {
        "populate_by_name": True,
    }


class FuturesAccountInfo(BaseModel):
    """期货账户信息

    币安U本位合约账户的完整信息。
    对应 GET /fapi/v3/account API 响应。

    用户在单资产模式和多资产模式下会看到不同结果：
    - 单资产模式：totalInitialMargin 等字段仅计算 USDT 资产
    - 多资产模式：totalInitialMargin 等字段以 USD 计价

    注意：此接口仅返回有持仓或挂单的交易对。

    V3 API 与 V2 API 的区别：
    - V3 不返回：feeTier, feeBurn, canTrade/canDeposit/canWithdraw, multiAssetsMargin, tradeGroupId, updateTime(顶层)
    """

    # ===== 账户余额（汇总）=====

    # 总保证金相关
    total_initial_margin: Optional[str] = Field(
        None, alias="totalInitialMargin",
        description="当前所需起始保证金总额(存在逐仓请忽略), 仅计算usdt资产"
    )
    total_maint_margin: Optional[str] = Field(
        None, alias="totalMaintMargin",
        description="维持保证金总额, 仅计算usdt资产"
    )
    total_wallet_balance: Optional[str] = Field(
        None, alias="totalWalletBalance",
        description="账户总余额, 仅计算usdt资产"
    )
    total_unrealized_profit: Optional[str] = Field(
        None, alias="totalUnrealizedProfit",
        description="持仓未实现盈亏总额, 仅计算usdt资产"
    )
    total_margin_balance: Optional[str] = Field(
        None, alias="totalMarginBalance",
        description="保证金总余额, 仅计算usdt资产"
    )

    # 持仓相关保证金
    total_position_initial_margin: Optional[str] = Field(
        None, alias="totalPositionInitialMargin",
        description="持仓所需起始保证金(基于最新标记价格), 仅计算usdt资产"
    )
    total_open_order_initial_margin: Optional[str] = Field(
        None, alias="totalOpenOrderInitialMargin",
        description="当前挂单所需起始保证金(基于最新标记价格), 仅计算usdt资产"
    )

    # 全仓相关
    total_cross_wallet_balance: Optional[str] = Field(
        None, alias="totalCrossWalletBalance",
        description="全仓账户余额, 仅计算usdt资产"
    )
    total_cross_unrealized_profit: Optional[str] = Field(
        None, alias="totalCrossUnPnl",
        description="全仓持仓未实现盈亏总额, 仅计算usdt资产"
    )

    # 可用余额
    available_balance: Optional[str] = Field(
        None, alias="availableBalance",
        description="可用余额, 仅计算usdt资产"
    )
    max_withdraw_amount: Optional[str] = Field(
        None, alias="maxWithdrawAmount",
        description="最大可转出余额, 仅计算usdt资产"
    )

    # ===== 详细列表 =====

    # 资产列表（每个资产的详细余额）
    assets: list[FuturesAsset] = Field(
        default_factory=list,
        description="资产列表，包含每个资产的余额和保证金信息"
    )

    # 持仓列表（仅有仓位或挂单的交易对会被返回）
    positions: list[FuturesPosition] = Field(
        default_factory=list,
        description="持仓列表"
    )

    model_config = {
        "populate_by_name": True,
    }
