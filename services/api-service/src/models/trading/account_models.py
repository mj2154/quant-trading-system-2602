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
    币安字段: a(asset), wb(wallet_balance), cw(cross_wallet_balance), bc(balance_change), m(reason)
    """

    model_config = ConfigDict(extra="ignore")

    asset: str = Field(description="资产名称")
    wallet_balance: str = Field(default="0", description="钱包余额")
    cross_wallet_balance: str = Field(default="0", description="全仓钱包余额")
    change_amount: str = Field(default="0", description="余额变动（不含盈亏和手续费）")
    reason: str = Field(default="", description="余额变动原因：DEPOSIT, WITHDRAW, ORDER, FUNDING_FEE等")


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
    币安字段: e, E, T, a
    """

    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(default="ACCOUNT_UPDATE", description="事件类型")
    event_time: int = Field(default=0, description="事件时间（毫秒）")
    transaction_time: int = Field(default=0, description="事务时间（毫秒）")
    a: dict[str, Any] = Field(default_factory=dict, description="更新数据（币安原始格式）")


class FuturesAccountUpdate(CamelCaseModel):
    """期货账户增量推送（WS订阅）

    对应 WS协议 ACCOUNT_UPDATE 事件。
    数据来源: Binance WebSocket User Data Stream (ACCOUNT_UPDATE)。

    使用场景: 订阅期货账户实时增量更新。
    """

    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(default="account_update", description="事件类型")
    subscription_key: str = Field(
        default="BINANCE:FUTURES@ACCOUNT", description="订阅键"
    )
    content: FuturesAccountUpdateContent = Field(description="推送内容")

    @classmethod
    def from_account_update_event(cls, event_data: dict[str, Any]) -> "FuturesAccountUpdate":
        """从币安 ACCOUNT_UPDATE 事件创建模型

        Args:
            event_data: 币安 WebSocket 推送的原始事件数据（简写字段格式）

        Returns:
            FuturesAccountUpdate 实例
        """
        # 直接使用原始 a 字段数据
        a_data = event_data.get("a", {})

        # 构建content内容
        content = FuturesAccountUpdateContent(
            event_type=event_data.get("e", "ACCOUNT_UPDATE"),
            event_time=event_data.get("E", 0),
            transaction_time=event_data.get("T", 0),
            a=a_data,
        )

        return cls(
            event_type="account_update",
            subscription_key="BINANCE:FUTURES@ACCOUNT",
            content=content,
        )


# =============================================================================
# 现货账户增量推送（WS订阅）
# =============================================================================


class SpotBalanceUpdate(CamelCaseModel):
    """现货余额更新

    对应 outboundAccountPosition 事件中的 B 字段。
    使用 alias 输出币安原始短字段名。
    """

    model_config = ConfigDict(extra="ignore")

    asset: str = Field(alias="a", description="资产名称")
    free: str = Field(alias="f", default="0", description="可用余额")
    locked: str = Field(alias="l", default="0", description="冻结余额")


class SpotAccountUpdateContent(CamelCaseModel):
    """现货账户更新内容

    对应 outboundAccountPosition 事件。
    使用 alias 输出币安原始短字段名 (e, E, u, B)。
    """

    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(alias="e", default="outboundAccountPosition", description="事件类型")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    last_update_time: int = Field(alias="u", default=0, description="账户最后更新时间（毫秒）")
    balances: list[SpotBalanceUpdate] = Field(alias="B", default_factory=list, description="余额列表")


class SpotAccountUpdate(CamelCaseModel):
    """现货账户增量推送（WS订阅）

    对应 WS协议 outboundAccountPosition 事件。
    数据来源: Binance WebSocket User Data Stream (outboundAccountPosition)。
    使用 alias 输出币安原始短字段名。

    使用场景: 订阅现货账户实时增量更新。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # 使用 alias 直接输出币安短字段名
    event_type: str = Field(alias="e", default="outboundAccountPosition", description="事件类型")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    last_update_time: int = Field(alias="u", default=0, description="账户最后更新时间（毫秒）")
    balances: list[SpotBalanceUpdate] = Field(alias="B", default_factory=list, description="余额列表")

    @classmethod
    def from_outbound_account_position(cls, event_data: dict[str, Any]) -> "SpotAccountUpdate":
        """从币安 outboundAccountPosition 事件创建模型

        Args:
            event_data: 币安 WebSocket 推送的原始事件数据

        Returns:
            SpotAccountUpdate 实例
        """
        # 解析余额更新 (B字段)
        balances = [
            SpotBalanceUpdate.model_validate(b)
            for b in event_data.get("B", [])
        ]

        return cls(
            event_type=event_data.get("e", "outboundAccountPosition"),
            event_time=event_data.get("E", 0),
            last_update_time=event_data.get("u", 0),
            balances=balances,
        )


class SpotBalanceUpdateEvent(CamelCaseModel):
    """现货余额更新事件（WS订阅）

    对应 WS协议 balanceUpdate 事件。
    数据来源: Binance WebSocket User Data Stream (balanceUpdate)。
    使用 alias 输出币安原始短字段名。

    使用场景: 充值/提现/转账时收到此事件。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_type: str = Field(alias="e", default="balanceUpdate", description="事件类型")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    asset: str = Field(alias="a", default="", description="资产名称")
    balance_delta: str = Field(alias="d", default="0", description="余额变化量")
    clear_time: int = Field(alias="T", default=0, description="清算时间（毫秒）")

    @classmethod
    def from_balance_update(cls, event_data: dict[str, Any]) -> "SpotBalanceUpdateEvent":
        """从币安 balanceUpdate 事件创建模型

        Args:
            event_data: 币安 WebSocket 推送的原始事件数据

        Returns:
            SpotBalanceUpdateEvent 实例
        """
        return cls(
            event_type=event_data.get("e", "balanceUpdate"),
            event_time=event_data.get("E", 0),
            asset=event_data.get("a", ""),
            balance_delta=event_data.get("d", "0"),
            clear_time=event_data.get("T", 0),
        )


class SpotExecutionReportEvent(CamelCaseModel):
    """现货订单执行报告事件（WS订阅）

    对应 WS协议 executionReport 事件。
    数据来源: Binance WebSocket User Data Stream (executionReport)。
    使用 alias 输出币安原始短字段名。

    使用场景: 订单状态更新（新建/成交/取消等）时收到此事件。

    参考: binance-docs/binance_spot_docs/User Data Stream.md
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # 必填字段
    event_type: str = Field(alias="e", default="executionReport", description="事件类型")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    symbol: str = Field(alias="s", default="", description="交易对")
    client_order_id: str = Field(alias="c", default="", description="客户端订单ID")
    side: str = Field(alias="S", default="", description="订单方向：BUY/SELL")
    order_type: str = Field(alias="o", default="", description="订单类型")
    order_id: int = Field(alias="i", default=0, description="订单ID")
    order_status: str = Field(alias="X", default="", description="订单状态")
    execution_type: str = Field(alias="x", default="", description="当前执行类型")

    # 可选字段（带默认值）
    time_in_force: str = Field(alias="f", default="GTC", description="有效期限")
    order_quantity: str = Field(alias="q", default="0", description="订单数量")
    order_price: str = Field(alias="p", default="0", description="订单价格")
    stop_price: str = Field(alias="P", default="0", description="止损价格")
    iceberg_quantity: str = Field(alias="F", default="0", description="冰山数量")
    order_list_id: int = Field(alias="g", default=-1, description="订单列表ID")
    original_client_order_id: str = Field(alias="C", default="", description="原订单ID")
    order_reject_reason: str = Field(alias="r", default="NONE", description="拒绝原因")
    last_executed_quantity: str = Field(alias="l", default="0", description="最近执行数量")
    cumulative_filled_quantity: str = Field(alias="z", default="0", description="累计成交数量")
    last_executed_price: str = Field(alias="L", default="0", description="最近执行价格")
    commission_amount: str = Field(alias="n", default="0", description="手续费金额")
    commission_asset: str | None = Field(alias="N", default=None, description="手续费资产")
    transaction_time: int = Field(alias="T", default=0, description="成交时间（毫秒）")
    trade_id: int = Field(alias="t", default=-1, description="成交ID")
    execution_id: int = Field(alias="I", default=0, description="执行ID")
    is_on_book: bool = Field(alias="w", default=False, description="是否在订单簿上")
    is_maker_side: bool = Field(alias="m", default=False, description="是否为 maker")
    is_ignore: bool = Field(alias="M", default=False, description="忽略")
    order_creation_time: int = Field(alias="O", default=0, description="订单创建时间（毫秒）")
    cumulative_quote_qty: str = Field(alias="Z", default="0", description="累计成交金额")
    last_quote_qty: str = Field(alias="Y", default="0", description="最近成交金额")
    quote_order_qty: str = Field(alias="Q", default="0", description="报价订单数量")
    working_time: int = Field(alias="W", default=0, description="工作时间（毫秒）")
    self_trade_prevention: str = Field(alias="V", default="NONE", description="自成交防止模式")

    @classmethod
    def from_execution_report(cls, event_data: dict[str, Any]) -> "SpotExecutionReportEvent":
        """从币安 executionReport 事件创建模型

        Args:
            event_data: 币安 WebSocket 推送的原始事件数据

        Returns:
            SpotExecutionReportEvent 实例
        """
        return cls(
            event_type=event_data.get("e", "executionReport"),
            event_time=event_data.get("E", 0),
            symbol=event_data.get("s", ""),
            client_order_id=event_data.get("c", ""),
            side=event_data.get("S", ""),
            order_type=event_data.get("o", ""),
            order_id=event_data.get("i", 0),
            order_status=event_data.get("X", ""),
            execution_type=event_data.get("x", ""),
            time_in_force=event_data.get("f", "GTC"),
            order_quantity=event_data.get("q", "0"),
            order_price=event_data.get("p", "0"),
            stop_price=event_data.get("P", "0"),
            iceberg_quantity=event_data.get("F", "0"),
            order_list_id=event_data.get("g", -1),
            original_client_order_id=event_data.get("C", ""),
            order_reject_reason=event_data.get("r", "NONE"),
            last_executed_quantity=event_data.get("l", "0"),
            cumulative_filled_quantity=event_data.get("z", "0"),
            last_executed_price=event_data.get("L", "0"),
            commission_amount=event_data.get("n", "0"),
            commission_asset=event_data.get("N"),
            transaction_time=event_data.get("T", 0),
            trade_id=event_data.get("t", -1),
            execution_id=event_data.get("I", 0),
            is_on_book=event_data.get("w", False),
            is_maker_side=event_data.get("m", False),
            is_ignore=event_data.get("M", False),
            order_creation_time=event_data.get("O", 0),
            cumulative_quote_qty=event_data.get("Z", "0"),
            last_quote_qty=event_data.get("Y", "0"),
            quote_order_qty=event_data.get("Q", "0"),
            working_time=event_data.get("W", 0),
            self_trade_prevention=event_data.get("V", "NONE"),
        )
