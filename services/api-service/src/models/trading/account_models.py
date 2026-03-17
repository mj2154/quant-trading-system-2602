"""
账户数据模型

对应设计文档 08-api-models.md 中的账户数据模型定义。
用于WS协议 ACCOUNT_DATA 响应的数据模型。

包含4种账户数据模型：
1. FuturesAccountData - GET请求获取期货账户完整快照
2. SpotAccountData - GET请求获取现货账户完整快照
3. FuturesAccountUpdate - WS订阅期货账户增量推送
4. SpotAccountUpdate - WS订阅现货账户增量推送

作者: Claude Code
版本: v1.0.0
"""

from typing import Any

from pydantic import ConfigDict, Field

from ..base import CamelCaseModel


# =============================================================================
# 期货账户信息（GET请求 - 完整快照）
# =============================================================================


class FuturesAccountAsset(CamelCaseModel):
    """期货账户资产详情

    对应 GET_FUTURES_ACCOUNT 响应中的 assets 数组元素。
    """

    model_config = ConfigDict(extra="ignore")

    asset: str = Field(description="资产名称（如 USDT, BUSD, BTC）")
    wallet_balance: str = Field(default="0", description="余额")
    unrealized_profit: str = Field(default="0", description="未实现盈亏")
    margin_balance: str = Field(default="0", description="保证金余额")
    maint_margin: str = Field(default="0", description="维持保证金")
    initial_margin: str = Field(default="0", description="当前所需起始保证金")
    position_initial_margin: str = Field(
        default="0", description="持仓所需起始保证金（基于最新标记价格）"
    )
    open_order_initial_margin: str = Field(
        default="0", description="当前挂单所需起始保证金（基于最新标记价格）"
    )
    cross_wallet_balance: str = Field(default="0", description="全仓账户余额")
    cross_un_pnl: str = Field(default="0", description="全仓持仓未实现盈亏")
    available_balance: str = Field(default="0", description="可用余额")
    max_withdraw_amount: str = Field(default="0", description="最大可转出余额")
    margin_available: bool = Field(default=True, description="该资产是否可用作多资产模式的保证金")
    update_time: int | None = Field(default=None, description="更新时间（毫秒）")


class FuturesAccountPosition(CamelCaseModel):
    """期货持仓详情

    对应 GET_FUTURES_ACCOUNT 响应中的 positions 数组元素。
    """

    model_config = ConfigDict(extra="ignore")

    symbol: str = Field(description="交易对符号（如 BTCUSDT）")
    initial_margin: str = Field(default="0", description="持仓所需起始保证金（基于最新标记价格）")
    maint_margin: str = Field(default="0", description="维持保证金")
    unrealized_profit: str = Field(default="0", description="持仓未实现盈亏")
    position_initial_margin: str = Field(
        default="0", description="持仓所需起始保证金（基于最新标记价格）"
    )
    open_order_initial_margin: str = Field(
        default="0", description="当前挂单所需起始保证金（基于最新标记价格）"
    )
    leverage: str = Field(default="1", description="当前杠杆倍数")
    isolated: bool = Field(default=False, description="是否为逐仓")
    entry_price: str = Field(default="0", description="平均入场价格")
    max_notional: str = Field(default="0", description="当前杠杆下的最大可用名义价值")
    bid_notional: str = Field(default="0", description="买单名义价值（忽略）")
    ask_notional: str = Field(default="0", description="卖单名义价值（忽略）")
    position_side: str = Field(default="BOTH", description="持仓方向: BOTH(单向), LONG(多头), SHORT(空头)")
    position_amt: str = Field(default="0", description="持仓数量")
    update_time: int | None = Field(default=None, description="更新时间（毫秒）")


class FuturesAccountDetail(CamelCaseModel):
    """期货账户详情（account字段内容）

    对应 GET_FUTURES_ACCOUNT 响应中的 account 对象。
    """

    model_config = ConfigDict(extra="ignore")

    total_initial_margin: str = Field(default="0", description="总初始保证金（仅 USDT 资产）")
    total_maint_margin: str = Field(default="0", description="总维持保证金（仅 USDT 资产）")
    total_wallet_balance: str = Field(default="0", description="总钱包余额（仅 USDT 资产）")
    total_unrealized_profit: str = Field(default="0", description="总未实现盈亏（仅 USDT 资产）")
    total_margin_balance: str = Field(default="0", description="总保证金余额（仅 USDT 资产）")
    total_position_initial_margin: str = Field(
        default="0", description="持仓所需初始保证金（仅 USDT 资产）"
    )
    total_open_order_initial_margin: str = Field(
        default="0", description="挂单所需初始保证金（仅 USDT 资产）"
    )
    total_cross_wallet_balance: str = Field(default="0", description="全仓钱包余额（仅 USDT 资产）")
    total_cross_un_pnl: str = Field(default="0", description="全仓未实现盈亏（仅 USDT 资产）")
    available_balance: str = Field(default="0", description="可用余额")
    max_withdraw_amount: str = Field(default="0", description="最大可转出金额")
    fee_tier: int = Field(default=0, description="账户手续费等级")
    fee_burn: bool = Field(default=False, description="是否开启手续费折扣: true=折扣开启, false=折扣关闭")
    multi_assets_margin: bool = Field(default=False, description="是否为多资产模式")
    trade_group_id: int | None = Field(default=None, description="交易组ID")
    update_time: int | None = Field(default=None, description="更新时间（毫秒）")
    assets: list[FuturesAccountAsset] = Field(default_factory=list, description="资产列表")
    positions: list[FuturesAccountPosition] = Field(default_factory=list, description="持仓列表")
    rate_limits: list[dict[str, Any]] = Field(default_factory=list, description="速率限制信息")


class FuturesAccountData(CamelCaseModel):
    """期货账户数据（GET请求响应）

    对应 WS协议 GET_FUTURES_ACCOUNT 响应。
    数据来源: Binance WebSocket API (v2/account.status)。

    使用场景: GET /api/v1/account/futures 获取期货账户完整快照。
    """

    model_config = ConfigDict(extra="ignore")

    account_type: str = Field(default="FUTURES", description="账户类型")
    account: FuturesAccountDetail = Field(description="账户详情")


# =============================================================================
# 现货账户信息（GET请求 - 完整快照）
# =============================================================================


class SpotCommissionRates(CamelCaseModel):
    """现货手续费率详情

    对应 GET_SPOT_ACCOUNT 响应中的 commissionRates 对象。
    """

    model_config = ConfigDict(extra="ignore")

    maker: str = Field(default="0", description="挂单手续费率")
    taker: str = Field(default="0", description="吃单手续费率")
    buyer: str = Field(default="0", description="买入手续费率")
    seller: str = Field(default="0", description="卖出手续费率")


class SpotBalance(CamelCaseModel):
    """现货余额详情

    对应 GET_SPOT_ACCOUNT 响应中的 balances 数组元素。
    """

    model_config = ConfigDict(extra="ignore")

    asset: str = Field(description="资产名称")
    free: str = Field(default="0", description="可用数量")
    locked: str = Field(default="0", description="锁定数量")


class SpotAccountDetail(CamelCaseModel):
    """现货账户详情（account字段内容）

    对应 GET_SPOT_ACCOUNT 响应中的 account 对象。
    """

    model_config = ConfigDict(extra="ignore")

    maker_commission: int = Field(default=0, description="挂单手续费率")
    taker_commission: int = Field(default=0, description="吃单手续费率")
    buyer_commission: int = Field(default=0, description="买入手续费率")
    seller_commission: int = Field(default=0, description="卖出手续费率")
    commission_rates: SpotCommissionRates | None = Field(
        default=None, description="手续费率详情"
    )
    can_trade: bool = Field(default=False, description="是否可以交易")
    can_withdraw: bool = Field(default=False, description="是否可以提现")
    can_deposit: bool = Field(default=False, description="是否可以充值")
    brokered: bool = Field(default=False, description="是否为经纪商账户")
    require_self_trade_prevention: bool = Field(
        default=False, description="是否需要自我交易预防"
    )
    prevent_sor: bool = Field(default=False, description="是否阻止 SOR")
    update_time: int | None = Field(default=None, description="最后更新时间（毫秒）")
    account_type: str = Field(default="SPOT", description="账户类型")
    balances: list[SpotBalance] = Field(default_factory=list, description="余额列表")
    permissions: list[str] = Field(default_factory=list, description="权限列表")
    uid: int | None = Field(default=None, description="用户ID")
    rate_limits: list[dict[str, Any]] = Field(default_factory=list, description="速率限制信息")


class SpotAccountData(CamelCaseModel):
    """现货账户数据（GET请求响应）

    对应 WS协议 GET_SPOT_ACCOUNT 响应。
    数据来源: Binance REST API (GET /api/v3/account)。

    使用场景: GET /api/v1/account/spot 获取现货账户完整快照。
    """

    model_config = ConfigDict(extra="ignore")

    account_type: str = Field(default="SPOT", description="账户类型")
    account: SpotAccountDetail = Field(description="账户详情")


# =============================================================================
# 期货账户增量推送（WS订阅）
# =============================================================================


class FuturesBalanceUpdate(CamelCaseModel):
    """期货余额更新

    对应 ACCOUNT_UPDATE 事件中的 B 字段。
    """

    model_config = ConfigDict(extra="ignore")

    asset: str = Field(description="资产名称")
    wallet_balance: str = Field(default="0", description="钱包余额")
    available_balance: str = Field(default="0", description="可用余额（扣除挂单保证金）")
    change_amount: str = Field(default="0", description="变更金额")


class FuturesPositionUpdate(CamelCaseModel):
    """期货持仓更新

    对应 ACCOUNT_UPDATE 事件中的 P 字段。
    """

    model_config = ConfigDict(extra="ignore")

    symbol: str = Field(description="交易对")
    position_amt: str = Field(default="0", description="持仓数量")
    entry_price: str = Field(default="0", description="开仓价格")
    break_even_price: str = Field(default="0", description="盈亏平衡价格")
    cum_realized_pnl: str = Field(default="0", description="费前累计实现盈亏")
    unrealized_pnl: str = Field(default="0", description="未实现盈亏")
    margin_type: str = Field(default="cross", description="保证金类型：isolated(逐仓) / cross(全仓)")
    isolated_wallet: str = Field(default="0", description="逐仓钱包余额")
    position_side: str = Field(default="BOTH", description="持仓方向：LONG, SHORT, BOTH")


class FuturesAccountUpdateContent(CamelCaseModel):
    """期货账户更新内容

    对应 ACCOUNT_UPDATE 事件的 content 字段。
    """

    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(default="ACCOUNT_UPDATE", description="事件类型")
    event_time: int = Field(default=0, description="事件时间（毫秒）")
    transaction_time: int = Field(default=0, description="事务时间（毫秒）")
    update_data: dict[str, Any] = Field(default_factory=dict, description="更新数据")


class FuturesAccountUpdate(CamelCaseModel):
    """期货账户增量推送（WS订阅）

    对应 WS协议 ACCOUNT_UPDATE 事件。
    数据来源: Binance WebSocket User Data Stream (ACCOUNT_UPDATE)。

    使用场景: 订阅期货账户实时增量更新。
    """

    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(default="account_update", description="事件类型")
    subscription_key: str = Field(
        default="BINANCE:ACCOUNT@FUTURES", description="订阅键"
    )
    content: dict[str, Any] = Field(default_factory=dict, description="推送内容")

    @classmethod
    def from_account_update_event(cls, event_data: dict[str, Any]) -> "FuturesAccountUpdate":
        """从币安 ACCOUNT_UPDATE 事件创建模型

        Args:
            event_data: 币安 WebSocket 推送的原始事件数据

        Returns:
            FuturesAccountUpdate 实例
        """
        # 解析余额更新 (B字段)
        balances = []
        for b in event_data.get("B", []):
            balances.append({
                "asset": b.get("a", ""),
                "walletBalance": b.get("wb", "0"),
                "availableBalance": b.get("cw", "0"),
                "changeAmount": b.get("bc", "0"),
            })

        # 解析持仓更新 (P字段)
        positions = []
        for p in event_data.get("P", []):
            positions.append({
                "symbol": p.get("s", ""),
                "positionAmt": p.get("pa", "0"),
                "entryPrice": p.get("ep", "0"),
                "breakEvenPrice": p.get("bep", "0"),
                "cumRealizedPnl": p.get("cr", "0"),
                "unrealizedPnl": p.get("up", "0"),
                "marginType": p.get("mt", "cross"),
                "isolatedWallet": p.get("iw", "0"),
                "positionSide": p.get("ps", "BOTH"),
            })

        # 构建content内容
        content = {
            "e": event_data.get("e", "ACCOUNT_UPDATE"),
            "E": event_data.get("E", 0),
            "T": event_data.get("T", 0),
            "a": {
                "m": event_data.get("a", {}).get("m", ""),
                "B": balances,
                "P": positions,
            },
        }

        return cls(
            event_type="account_update",
            subscription_key="BINANCE:ACCOUNT@FUTURES",
            content=content,
        )


# =============================================================================
# 现货账户增量推送（WS订阅）
# =============================================================================


class SpotBalanceUpdate(CamelCaseModel):
    """现货余额更新

    对应 outboundAccountPosition 事件中的 B 字段。
    """

    model_config = ConfigDict(extra="ignore")

    asset: str = Field(description="资产名称")
    free: str = Field(default="0", description="可用余额")
    locked: str = Field(default="0", description="冻结余额")


class SpotAccountUpdateContent(CamelCaseModel):
    """现货账户更新内容

    对应 outboundAccountPosition 事件的 content 字段。
    """

    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(default="outboundAccountPosition", description="事件类型")
    event_time: int = Field(default=0, description="事件时间（毫秒）")
    last_update_time: int = Field(default=0, description="账户最后更新时间（毫秒）")
    balances: list[dict[str, Any]] = Field(default_factory=list, description="余额列表")


class SpotAccountUpdate(CamelCaseModel):
    """现货账户增量推送（WS订阅）

    对应 WS协议 outboundAccountPosition 事件。
    数据来源: Binance WebSocket User Data Stream (outboundAccountPosition)。

    使用场景: 订阅现货账户实时增量更新。
    """

    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(default="account_update", description="事件类型")
    subscription_key: str = Field(
        default="BINANCE:ACCOUNT@SPOT", description="订阅键"
    )
    content: dict[str, Any] = Field(default_factory=dict, description="推送内容")

    @classmethod
    def from_account_position_event(cls, event_data: dict[str, Any]) -> "SpotAccountUpdate":
        """从币安 outboundAccountPosition 事件创建模型

        Args:
            event_data: 币安 WebSocket 推送的原始事件数据

        Returns:
            SpotAccountUpdate 实例
        """
        # 解析余额更新 (B字段)
        balances = []
        for b in event_data.get("B", []):
            balances.append({
                "asset": b.get("a", ""),
                "free": b.get("f", "0"),
                "locked": b.get("l", "0"),
            })

        # 构建content内容
        content = {
            "e": event_data.get("e", "outboundAccountPosition"),
            "E": event_data.get("E", 0),
            "u": event_data.get("u", 0),
            "B": balances,
        }

        return cls(
            event_type="account_update",
            subscription_key="BINANCE:ACCOUNT@SPOT",
            content=content,
        )
