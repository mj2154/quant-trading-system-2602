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
    使用 alias 输出币安原始短字段名，与官方文档一致。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    asset: str = Field(alias="a", description="资产名称")
    wallet_balance: str = Field(alias="wb", default="0", description="钱包余额")
    cross_wallet_balance: str = Field(alias="cw", default="0", description="全仓钱包余额")
    change_amount: str = Field(alias="bc", default="0", description="余额变动（不含盈亏和手续费）")
    reason: str = Field(alias="m", default="", description="余额变动原因：DEPOSIT, WITHDRAW, ORDER, FUNDING_FEE等")


class FuturesPositionUpdate(CamelCaseModel):
    """期货持仓更新

    对应 ACCOUNT_UPDATE 事件中的 P 字段。
    使用 alias 输出币安原始短字段名，与官方文档一致。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    symbol: str = Field(alias="s", description="交易对")
    position_amt: str = Field(alias="pa", default="0", description="持仓数量")
    entry_price: str = Field(alias="ep", default="0", description="开仓价格")
    break_even_price: str = Field(alias="bep", default="0", description="盈亏平衡价格")
    cum_realized_pnl: str = Field(alias="cr", default="0", description="费前累计实现盈亏")
    unrealized_pnl: str = Field(alias="up", default="0", description="未实现盈亏")
    margin_type: str = Field(alias="mt", default="cross", description="保证金类型：isolated(逐仓) / cross(全仓)")
    isolated_wallet: str = Field(alias="iw", default="0", description="逐仓钱包余额")
    position_side: str = Field(alias="ps", default="BOTH", description="持仓方向：LONG, SHORT, BOTH")


class FuturesAccountUpdateContent(CamelCaseModel):
    """期货账户更新内容（对应 a 字段）

    严格遵循币安官方文档格式。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    reason: str = Field(alias="m", default="", description="余额变动原因：ORDER, FUNDING_FEE, WITHDRAW, DEPOSIT等")
    balances: list[FuturesBalanceUpdate] = Field(alias="B", default_factory=list, description="余额更新列表")
    positions: list[FuturesPositionUpdate] = Field(alias="P", default_factory=list, description="持仓更新列表")


class FuturesAccountUpdate(CamelCaseModel):
    """期货账户增量推送（WS订阅）

    对应 WS协议 ACCOUNT_UPDATE 事件。
    数据来源: Binance WebSocket User Data Stream (ACCOUNT_UPDATE)。

    严格遵循币安官方文档格式：
    - e: 事件类型 (ACCOUNT_UPDATE)
    - E: 事件时间（毫秒）
    - T: 事务时间（毫秒）
    - a: 更新数据（含 m, B, P）

    使用场景: 订阅期货账户实时增量更新。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # 币安原始字段 - 严格按官方文档定义
    event_type: str = Field(alias="e", default="", description="事件类型：ACCOUNT_UPDATE")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    transaction_time: int = Field(alias="T", default=0, description="事务时间（毫秒）")

    # 更新数据内容（对应 a 字段 - 嵌套结构）
    update_data: FuturesAccountUpdateContent = Field(alias="a", description="更新数据")

    @classmethod
    def from_account_update_event(cls, event_data: dict[str, Any]) -> FuturesAccountUpdate:
        """从币安 ACCOUNT_UPDATE 事件创建模型

        Args:
            event_data: 币安 WebSocket 推送的原始事件数据
                包含 e, E, T, a 字段

        Returns:
            FuturesAccountUpdate 实例
        """
        # 构建嵌套的 update_data 结构
        update_data_dict = {
            "m": event_data.get("a", {}).get("m", ""),
            "B": [
                FuturesBalanceUpdate.model_validate(b).model_dump(by_alias=True)
                for b in event_data.get("a", {}).get("B", [])
            ],
            "P": [
                FuturesPositionUpdate.model_validate(p).model_dump(by_alias=True)
                for p in event_data.get("a", {}).get("P", [])
            ],
        }

        # 构建完整的 event_data 字典，使用 alias 作为键
        full_dict = {
            "e": event_data.get("e", ""),
            "E": event_data.get("E", 0),
            "T": event_data.get("T", 0),
            "a": update_data_dict,
        }

        return cls.model_validate(full_dict)


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
    def from_outbound_account_position(cls, event_data: dict[str, Any]) -> SpotAccountUpdate:
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

        # 构建更新后的 event_data（包含解析后的 balances）
        full_data = {
            **event_data,
            "B": [b.model_dump(by_alias=True) for b in balances],
        }
        return cls.model_validate(full_data)


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
    def from_balance_update(cls, event_data: dict[str, Any]) -> SpotBalanceUpdateEvent:
        """从币安 balanceUpdate 事件创建模型

        Args:
            event_data: 币安 WebSocket 推送的原始事件数据

        Returns:
            SpotBalanceUpdateEvent 实例
        """
        return cls.model_validate(event_data)


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
    def from_execution_report(cls, event_data: dict[str, Any]) -> SpotExecutionReportEvent:
        """从币安 executionReport 事件创建模型

        Args:
            event_data: 币安 WebSocket 推送的原始事件数据

        Returns:
            SpotExecutionReportEvent 实例
        """
        return cls.model_validate(event_data)


class FuturesOrderTradeUpdate(CamelCaseModel):
    """期货订单成交更新（WS订阅）

    对应 WS协议 ORDER_TRADE_UPDATE 事件。
    数据来源: Binance WebSocket User Data Stream (ORDER_TRADE_UPDATE)。

    严格遵循币安官方文档格式：
    - e: 事件类型 (ORDER_TRADE_UPDATE)
    - E: 事件时间（毫秒）
    - T: 事务时间（毫秒）
    - o: 订单数据
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_type: str = Field(alias="e", default="", description="事件类型：ORDER_TRADE_UPDATE")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    transaction_time: int = Field(alias="T", default=0, description="事务时间（毫秒）")
    order_data: dict = Field(alias="o", description="订单数据")

    @classmethod
    def from_order_trade_update_event(cls, event_data: dict[str, Any]) -> FuturesOrderTradeUpdate:
        return cls.model_validate(event_data)


class FuturesTradeLiteEvent(CamelCaseModel):
    """期货简化交易事件（WS订阅）

    对应 WS协议 TRADE_LITE 事件。
    数据来源: Binance WebSocket User Data Stream (TRADE_LITE)。

    严格遵循币安官方文档格式（参考 BinanceFuturesTradeLiteWSModel）：
    - e: 事件类型 (TRADE_LITE)
    - E: 事件时间（毫秒）
    - T: 事务时间（毫秒）
    - s: 交易对
    - t: 成交ID
    - i: 订单ID
    - p: 原始价格
    - q: 原始数量
    - S: 订单方向
    - m: 是否为做市商
    - c: 客户端订单ID
    - L: 最近成交价格
    - l: 最近成交数量
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_type: str = Field(alias="e", default="", description="事件类型：TRADE_LITE")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    transaction_time: int = Field(alias="T", default=0, description="事务时间（毫秒）")
    symbol: str = Field(alias="s", default="", description="交易对")
    trade_id: int = Field(alias="t", default=0, description="成交ID")
    order_id: int = Field(alias="i", default=0, description="订单ID")
    original_price: str = Field(alias="p", default="0", description="原始价格")
    original_quantity: str = Field(alias="q", default="0", description="原始数量")
    side: str = Field(alias="S", default="", description="订单方向：BUY/SELL")
    is_maker: bool = Field(alias="m", default=False, description="是否为做市商")
    client_order_id: str = Field(alias="c", default="", description="客户端订单ID")
    last_filled_price: str = Field(alias="L", default="0", description="最近成交价格")
    last_filled_quantity: str = Field(alias="l", default="0", description="最近成交数量")


# =============================================================================
# 期货账户配置更新（WS订阅）
# =============================================================================


class FuturesAccountConfigLeverageUpdate(CamelCaseModel):
    """期货账户配置 - 杠杆更新

    对应 ACCOUNT_CONFIG_UPDATE 事件中的 ac 字段。
    使用 alias 输出币安原始短字段名。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    symbol: str = Field(alias="s", default="", description="交易对符号")
    leverage: int = Field(alias="l", default=1, description="杠杆倍数")


class FuturesAccountConfigMultiAssetUpdate(CamelCaseModel):
    """期货账户配置 - 多资产模式更新

    对应 ACCOUNT_CONFIG_UPDATE 事件中的 ai 字段。
    使用 alias 输出币安原始短字段名。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    multi_asset_mode: bool = Field(alias="j", default=False, description="多资产模式")


class FuturesAccountConfigUpdate(CamelCaseModel):
    """期货账户配置更新（WS订阅）

    对应 WS协议 ACCOUNT_CONFIG_UPDATE 事件。
    数据来源: Binance WebSocket User Data Stream (ACCOUNT_CONFIG_UPDATE)。

    严格遵循币安官方文档格式：
    - e: 事件类型 (ACCOUNT_CONFIG_UPDATE)
    - E: 事件时间（毫秒）
    - T: 事务时间（毫秒）
    - ac: 杠杆配置（可选）
    - ai: 多资产模式配置（可选）

    注意：事件可能只包含 ac 或 ai 之一，不会同时包含。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_type: str = Field(alias="e", default="ACCOUNT_CONFIG_UPDATE", description="事件类型")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    transaction_time: int = Field(alias="T", default=0, description="事务时间（毫秒）")
    leverage_update: FuturesAccountConfigLeverageUpdate | None = Field(
        default=None, alias="ac", description="杠杆配置更新"
    )
    multi_asset_update: FuturesAccountConfigMultiAssetUpdate | None = Field(
        default=None, alias="ai", description="多资产模式更新"
    )

    @classmethod
    def from_account_config_update_event(cls, event_data: dict[str, Any]) -> FuturesAccountConfigUpdate:
        """从币安 ACCOUNT_CONFIG_UPDATE 事件创建模型

        Args:
            event_data: 币安 WebSocket 推送的原始事件数据

        Returns:
            FuturesAccountConfigUpdate 实例
        """
        leverage_update = None
        if event_data.get("ac"):
            leverage_update = FuturesAccountConfigLeverageUpdate.model_validate(event_data["ac"])

        multi_asset_update = None
        if event_data.get("ai"):
            multi_asset_update = FuturesAccountConfigMultiAssetUpdate.model_validate(event_data["ai"])

        return cls.model_validate(event_data)


# =============================================================================
# 期货保证金追缴（WS订阅）
# =============================================================================


class FuturesMarginCallPosition(CamelCaseModel):
    """期货保证金追缴持仓项

    对应 MARGIN_CALL 事件中的 p 字段。
    使用 alias 输出币安原始短字段名。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    symbol: str = Field(alias="s", default="", description="交易对")
    position_side: str = Field(alias="ps", default="BOTH", description="持仓方向：LONG, SHORT, BOTH")
    position_amt: str = Field(alias="pa", default="0", description="持仓数量")
    margin_type: str = Field(alias="mt", default="cross", description="保证金类型：cross(全仓), isolated(逐仓)")
    isolated_wallet: str = Field(alias="iw", default="0", description="逐仓钱包")
    mark_price: str = Field(alias="mp", default="0", description="标记价格")
    unrealized_profit: str = Field(alias="up", default="0", description="未实现盈亏")
    maintenance_margin_required: str = Field(alias="mm", default="0", description="维持保证金要求")


class FuturesMarginCallEvent(CamelCaseModel):
    """期货保证金追缴事件（WS订阅）

    对应 WS协议 MARGIN_CALL 事件。
    数据来源: Binance WebSocket User Data Stream (MARGIN_CALL)。

    严格遵循币安官方文档格式：
    - e: 事件类型 (MARGIN_CALL)
    - E: 事件时间（毫秒）
    - cw: 跨账户钱包余额
    - p: 追缴持仓列表

    这是高优先级事件，涉及强平风险，需要及时告警。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_type: str = Field(alias="e", default="MARGIN_CALL", description="事件类型")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    cross_wallet_balance: str = Field(alias="cw", default="0", description="跨账户钱包余额")
    positions: list[FuturesMarginCallPosition] = Field(
        alias="p", default_factory=list, description="追缴持仓列表"
    )


# =============================================================================
# 期货条件单更新（WS订阅）
# =============================================================================


class FuturesAlgoOrderData(CamelCaseModel):
    """期货条件单数据

    对应 ALGO_UPDATE 事件中的 o 字段。
    使用 alias 输出币安原始短字段名。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    client_algo_id: str = Field(alias="caid", default="", description="客户端算法订单ID")
    algo_id: int = Field(alias="aid", default=0, description="算法订单ID")
    algo_type: str = Field(alias="at", default="", description="算法类型")
    order_type: str = Field(alias="o", default="", description="订单类型")
    symbol: str = Field(alias="s", default="", description="交易对")
    side: str = Field(alias="S", default="", description="订单方向：BUY/SELL")
    position_side: str = Field(alias="ps", default="BOTH", description="持仓方向")
    time_in_force: str = Field(alias="f", default="GTC", description="有效期限")
    quantity: str = Field(alias="q", default="0", description="数量")
    algo_status: str = Field(alias="X", default="", description="算法订单状态")
    algo_order_id: str = Field(alias="ai", default="", description="算法订单ID")
    avg_fill_price: str = Field(alias="ap", default="0", description="平均成交价格")
    executed_quantity: str = Field(alias="aq", default="0", description="已成交数量")
    actual_order_type: str = Field(alias="act", default="", description="实际订单类型")
    trigger_price: str = Field(alias="tp", default="0", description="触发价格")
    order_price: str = Field(alias="p", default="0", description="订单价格")
    stp_mode: str = Field(alias="V", default="", description="STP模式")
    working_type: str = Field(alias="wt", default="", description="工作类型")
    price_match: str = Field(alias="pm", default="", description="价格匹配模式")
    if_close_all: bool = Field(alias="cp", default=False, description="是否全平")
    if_price_protect: bool = Field(alias="pP", default=False, description="是否开启价格保护")
    is_reduce_only: bool = Field(alias="R", default=False, description="是否仅减仓")
    trigger_time: int = Field(alias="tt", default=0, description="触发时间")
    good_till_date: int = Field(alias="gtd", default=0, description="GTD有效期")
    reject_reason: str = Field(alias="rm", default="", description="拒绝原因")


class FuturesAlgoUpdateEvent(CamelCaseModel):
    """期货条件单更新事件（WS订阅）

    对应 WS协议 ALGO_UPDATE 事件。
    数据来源: Binance WebSocket User Data Stream (ALGO_UPDATE)。

    严格遵循币安官方文档格式：
    - e: 事件类型 (ALGO_UPDATE)
    - T: 事务时间（毫秒）
    - E: 事件时间（毫秒）
    - o: 订单数据
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_type: str = Field(alias="e", default="ALGO_UPDATE", description="事件类型")
    transaction_time: int = Field(alias="T", default=0, description="事务时间（毫秒）")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    order_data: FuturesAlgoOrderData = Field(alias="o", description="订单数据")


# =============================================================================
# 期货策略更新（WS订阅）
# =============================================================================


class FuturesStrategyData(CamelCaseModel):
    """期货策略数据

    对应 STRATEGY_UPDATE 事件中的 su 字段。
    使用 alias 输出币安原始短字段名。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    strategy_id: int = Field(alias="si", default=0, description="策略ID")
    strategy_type: str = Field(alias="st", default="", description="策略类型")
    strategy_status: str = Field(alias="ss", default="", description="策略状态")
    symbol: str = Field(alias="s", default="", description="交易对")
    update_time: int = Field(alias="ut", default=0, description="更新时间")
    op_code: int = Field(alias="c", default=0, description="操作代码")


class FuturesStrategyUpdateEvent(CamelCaseModel):
    """期货策略更新事件（WS订阅）

    对应 WS协议 STRATEGY_UPDATE 事件。
    数据来源: Binance WebSocket User Data Stream (STRATEGY_UPDATE)。

    严格遵循币安官方文档格式：
    - e: 事件类型 (STRATEGY_UPDATE)
    - T: 事务时间（毫秒）
    - E: 事件时间（毫秒）
    - su: 策略数据
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_type: str = Field(alias="e", default="STRATEGY_UPDATE", description="事件类型")
    transaction_time: int = Field(alias="T", default=0, description="事务时间（毫秒）")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    strategy_data: FuturesStrategyData = Field(alias="su", description="策略数据")


# =============================================================================
# 期货网格更新（WS订阅）
# =============================================================================


class FuturesGridData(CamelCaseModel):
    """期货网格数据

    对应 GRID_UPDATE 事件中的 gu 字段。
    使用 alias 输出币安原始短字段名。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    strategy_id: int = Field(alias="si", default=0, description="策略ID")
    strategy_type: str = Field(alias="st", default="", description="策略类型")
    strategy_status: str = Field(alias="ss", default="", description="策略状态")
    symbol: str = Field(alias="s", default="", description="交易对")
    realized_pnl: str = Field(alias="r", default="0", description="已实现盈亏")
    unmatched_avg_price: str = Field(alias="up", default="0", description="未成交平均价格")
    unmatched_qty: str = Field(alias="uq", default="0", description="未成交数量")
    unmatched_fee: str = Field(alias="uf", default="0", description="未成交手续费")
    matched_pnl: str = Field(alias="mp", default="0", description="已匹配盈亏")
    update_time: int = Field(alias="ut", default=0, description="更新时间")


class FuturesGridUpdateEvent(CamelCaseModel):
    """期货网格更新事件（WS订阅）

    对应 WS协议 GRID_UPDATE 事件。
    数据来源: Binance WebSocket User Data Stream (GRID_UPDATE)。

    严格遵循币安官方文档格式：
    - e: 事件类型 (GRID_UPDATE)
    - T: 事务时间（毫秒）
    - E: 事件时间（毫秒）
    - gu: 网格数据
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_type: str = Field(alias="e", default="GRID_UPDATE", description="事件类型")
    transaction_time: int = Field(alias="T", default=0, description="事务时间（毫秒）")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    grid_data: FuturesGridData = Field(alias="gu", description="网格数据")


# =============================================================================
# 期货条件单触发拒绝（WS订阅）
# =============================================================================


class FuturesConditionalOrderRejectData(CamelCaseModel):
    """期货条件单拒绝数据

    对应 CONDITIONAL_ORDER_TRIGGER_REJECT 事件中的 or 字段。
    使用 alias 输出币安原始短字段名。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    symbol: str = Field(alias="s", default="", description="交易对")
    order_id: int = Field(alias="i", default=0, description="订单ID")
    reject_reason: str = Field(alias="r", default="", description="拒绝原因")


class FuturesConditionalOrderTriggerRejectEvent(CamelCaseModel):
    """期货条件单触发拒绝事件（WS订阅）

    对应 WS协议 CONDITIONAL_ORDER_TRIGGER_REJECT 事件。
    数据来源: Binance WebSocket User Data Stream (CONDITIONAL_ORDER_TRIGGER_REJECT)。

    严格遵循币安官方文档格式：
    - e: 事件类型 (CONDITIONAL_ORDER_TRIGGER_REJECT)
    - E: 事件时间（毫秒）
    - T: 事务时间（毫秒）
    - or: 拒绝数据
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_type: str = Field(alias="e", default="CONDITIONAL_ORDER_TRIGGER_REJECT", description="事件类型")
    event_time: int = Field(alias="E", default=0, description="事件时间（毫秒）")
    transaction_time: int = Field(alias="T", default=0, description="事务时间（毫秒）")
    reject_data: FuturesConditionalOrderRejectData = Field(alias="or", description="拒绝数据")
