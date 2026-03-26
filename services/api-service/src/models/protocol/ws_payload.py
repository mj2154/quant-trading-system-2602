"""
WebSocket数据载荷模型

定义WebSocket消息中的data字段载荷模型。

严格遵循设计文档: docs/backend/design/07-websocket-protocol.md

作者: Claude Code
版本: v2.0.0
"""


from pydantic import Field

# 使用本地基类进行命名转换
from ..base import CamelCaseModel

# 从 db 模块导入数据模型
from ..db.signal_models import StrategyMetadataResponse

# 从 trading 模块导入数据模型
from ..trading.account_models import FuturesAccountData, SpotAccountData

# ==================== 数据载荷模型 ====================


class SymbolType(CamelCaseModel):
    """
    TradingView 标的类型

    用于 ConfigData.symbols_types 字段。
    设计文档: 07-websocket-protocol.md 1.1.1 CONFIG_DATA 数据模型定义
    """

    name: str  # 显示名称
    value: str  # 值


class ConfigData(CamelCaseModel):
    """
    配置数据载荷模型

    TradingView数据源配置信息。
    用于WebSocket响应的data字段载荷。

    设计文档: 07-websocket-protocol.md 1.1.1 CONFIG_DATA 数据模型定义
    """

    supports_search: bool = True  # 支持搜索
    supports_group_request: bool = False  # 支持分组请求
    supports_marks: bool = False  # 支持标记
    supports_timescale_marks: bool = False  # 支持时间轴标记
    supports_time: bool = True  # 支持时间
    supported_resolutions: list[str] = [
        "1",
        "5",
        "15",
        "60",
        "240",
        "1D",
        "1W",
        "1M",
    ]  # 支持的分辨率
    currency_codes: list[str] = [
        "USDT",
        "BTC",
        "ETH",
        "BNB",
        "BUSD",
        "USDC",
        "FDUSD",
    ]  # 支持的货币代码
    symbols_types: list[SymbolType] = []  # 标的类型


class SymbolSearchItem(CamelCaseModel):
    """
    搜索结果中的单个交易对项

    用于 SearchSymbolsData.symbols 字段。

    设计文档: 07-websocket-protocol.md 1.2.1 搜索结果数据模型定义
    """

    symbol: str  # 标的全名（格式：EXCHANGE:SYMBOL）
    full_name: str  # 标的全名（与 symbol 相同）
    description: str  # 标的描述
    exchange: str  # 交易所
    ticker: str  # 交易代码
    type: str  # 标的类型 (crypto)


class SearchSymbolsData(CamelCaseModel):
    """
    搜索交易对数据载荷模型

    用于WebSocket响应的data字段载荷。

    设计文档: 07-websocket-protocol.md 1.2.1 搜索结果数据模型定义
    """

    symbols: list[SymbolSearchItem]  # 交易对列表
    total: int  # 总数量
    count: int  # 当前返回数量


class ServerTimeData(CamelCaseModel):
    """
    服务器时间数据载荷模型

    用于WebSocket响应的data字段载荷。

    设计文档: 07-websocket-protocol.md - 1.5 获取服务器时间
    """

    server_time: int  # 服务器时间（毫秒时间戳，来源于 Binance API）


class FailedSubscription(CamelCaseModel):
    """
    失败的订阅项

    用于 SubscribeData.failed 字段。
    设计文档: 07-websocket-protocol.md
    """

    subscription_key: str  # 订阅键
    reason: str  # 失败原因


class SubscribeData(CamelCaseModel):
    """
    订阅响应数据载荷模型

    用于WebSocket响应的data字段载荷。
    支持部分成功情况。
    """

    status: str = "success"  # 状态：success/partial
    subscriptions: list[str]  # 成功的订阅键列表（v2.0格式）
    failed: list[FailedSubscription] | None = None  # 失败的订阅列表


class UnsubscribeData(CamelCaseModel):
    """
    取消订阅响应数据载荷模型

    用于WebSocket响应的data字段载荷。
    """

    status: str = "success"  # 状态


class SubscriptionItem(CamelCaseModel):
    """
    单个订阅信息

    用于 SubscriptionsData.subscriptions 字段。
    设计文档: 07-websocket-protocol.md 1.6.1 SUBSCRIPTION_DATA 数据模型定义
    """

    subscription_key: str  # 订阅键（v2.0格式）
    data_type: str  # 数据类型（kline/quotes/trade）
    exchange: str  # 交易所代码
    symbol: str  # 交易对代码
    interval: str | None = None  # 分辨率（如适用）
    product_type: str  # 产品类型（spot/perpetual/quarterly）
    status: str  # 订阅状态（active/inactive/error）
    subscribed_at: int  # 订阅时间戳
    message_count: int = 0  # 接收到的消息数量
    last_message_at: int | None = None  # 最后一条消息时间戳


class SubscriptionsData(CamelCaseModel):
    """
    查询订阅响应数据载荷模型

    用于WebSocket响应的data字段载荷。
    设计文档: 07-websocket-protocol.md 1.6.1 SUBSCRIPTION_DATA 数据模型定义
    """

    type: str = "subscriptions"
    subscriptions: list[SubscriptionItem]  # 订阅列表
    total: int = 0  # 总订阅数
    active_count: int = 0  # 活跃订阅数
    inactive_count: int = 0  # 非活跃订阅数


class SystemMetrics(CamelCaseModel):
    """
    系统指标数据

    用于 MetricsData.metrics 字段。
    设计文档: 07-websocket-protocol.md 1.5.1 METRICS_DATA 数据模型定义
    """

    pending_tasks: int = 0  # 待处理任务数
    connected_clients: int = 0  # 活跃连接数


class MetricsData(CamelCaseModel):
    """
    指标查询响应数据载荷模型

    用于WebSocket响应的data字段载荷。
    设计文档: 07-websocket-protocol.md 1.5.1 METRICS_DATA 数据模型定义
    """

    type: str = "metrics"  # 数据类型
    metrics: SystemMetrics  # 指标数据
    active_connections: int = 0  # 活跃连接数（冗余，为兼容性）
    subscription_count: int = 0  # 订阅数量（冗余，为兼容性）


class OrderResultData(CamelCaseModel):
    """订单结果数据模型

    用于存储币安 API 返回的订单信息。
    支持现货和期货订单响应的所有字段。

    设计文档: docs/backend/design/08-api-models.md
    使用 extra="allow" 允许灵活处理不同市场类型的字段差异。
    序列化时会自动将内部 snake_case 转换为前端需要的 camelCase。
    """

    # 核心订单标识（通用字段）
    order_id: int | None = Field(None, description="币安订单ID")
    client_order_id: str | None = Field(None, description="客户端订单ID")
    symbol: str | None = Field(None, description="交易对")

    # 订单状态
    status: str | None = Field(None, description="订单状态")

    # 订单方向和类型
    side: str | None = Field(None, description="订单方向 BUY/SELL")
    order_type: str | None = Field(None, description="订单类型")
    position_side: str | None = Field(None, description="持仓方向")

    # 数量和价格
    orig_qty: str | None = Field(None, description="原始数量")
    price: str | None = Field(None, description="价格")
    avg_price: str | None = Field(None, description="平均价格")
    executed_qty: str | None = Field(None, description="已执行数量")
    cum_qty: str | None = Field(None, description="累计数量")
    cum_quote: str | None = Field(None, description="累计报价")

    # 时间相关
    time_in_force: str | None = Field(None, description="时间策略")
    transact_time: int | None = Field(None, description="交易时间")
    update_time: int | None = Field(None, description="更新时间")

    # 止损止盈
    stop_price: str | None = Field(None, description="止损价格")

    # 期货特有
    reduce_only: bool | None = Field(None, description="是否只减仓")
    close_position: bool | None = Field(None, description="是否平仓")

    # 现货特有
    iceberg_qty: str | None = Field(None, description="冰山数量")

    # 其他
    is_working: bool | None = Field(None, description="是否正在运行")
    working_time: int | None = Field(None, description="工作时间")

    # 允许额外字段（兼容不同市场的响应差异）
    model_config = {"extra": "allow"}


class OrderPayloadData(CamelCaseModel):
    """订单请求参数数据模型

    用于存储下单时传入的参数（用于前端回显）。
    支持现货和期货订单请求的所有字段。

    设计文档: docs/backend/design/08-api-models.md
    """

    # 核心字段
    symbol: str | None = Field(None, description="交易对")
    side: str | None = Field(None, description="订单方向")
    order_type: str | None = Field(None, description="订单类型")
    quantity: float | None = Field(None, description="数量")

    # 订单标识
    new_client_order_id: str | None = Field(None, description="客户端订单ID")

    # 价格相关
    price: float | None = Field(None, description="价格")
    stop_price: float | None = Field(None, description="止损价格")
    time_in_force: str | None = Field(None, description="时间策略")

    # 期货特有
    position_side: str | None = Field(None, description="持仓方向")
    reduce_only: bool | None = Field(None, description="是否只减仓")

    # 允许额外字段
    model_config = {"extra": "allow"}


class OrderResponseData(CamelCaseModel):
    """订单响应数据模型

    用于 WebSocket 订单操作响应（CREATE_ORDER, GET_ORDER, CANCEL_ORDER）。
    严格遵循设计文档: docs/backend/design/07-websocket-protocol.md 和 08-api-models.md

    字段说明:
    - type: 固定值 "order"
    - status: 任务状态 COMPLETED / FAILED
    - task_id: order_tasks 表的任务 ID
    - result: 币安 API 返回的订单信息（成功时）
    - payload: 下单时传入的参数（用于前端回显）
    """

    type: str = "order"
    status: str
    task_id: int | None = None
    result: OrderResultData | None = None
    payload: OrderPayloadData | None = None


class AccountResponseData(CamelCaseModel):
    """账户响应数据模型

    用于 WebSocket 账户信息响应（GET_FUTURES_ACCOUNT, GET_SPOT_ACCOUNT）。
    严格遵循设计文档: docs/backend/design/07-websocket-protocol.md

    设计文档规定格式:
    {
        "data": {
            "account": {
                // 账户详细信息
            }
        }
    }

    字段说明:
    - account: 账户详细信息（FuturesAccountData 或 SpotAccountData）
    """

    account: FuturesAccountData | SpotAccountData | None = None


# ==================== 实时推送载荷 ====================


class SignalData(CamelCaseModel):
    """信号数据推送载荷模型

    用于 WebSocket 实时信号推送（subscriptionKey 以 SIGNAL: 开头）。
    与 SignalRecordResponse 保持一致，但字段名为 camelCase。

    严格遵循设计文档: docs/backend/design/07-websocket-protocol.md
    """

    id: int = Field(..., description="信号数据库自增ID")
    alert_id: str = Field(..., description="关联的告警配置ID (UUID)")
    name: str = Field(..., description="告警配置名称（冗余存储，保留信号产生时的告警名称）")
    strategy_type: str = Field(..., description="策略类型")
    symbol: str = Field(..., description="交易对")
    interval: str = Field(..., description="K线周期")
    trigger_type: str | None = Field(None, description="触发类型")
    signal_value: bool | None = Field(
        None, description="信号值: true=做多, false=做空, null=无信号"
    )
    signal_reason: str | None = Field(None, description="信号原因")
    computed_at: str = Field(..., description="信号计算时间")
    source_subscription_key: str | None = Field(None, description="触发该信号的订阅键")
    created_by: str | None = Field(None, description="创建者标识")


class AckData(CamelCaseModel):
    """ACK 确认数据载荷

    用于 ACK 响应的 data 字段。
    设计文档: 07-websocket-protocol.md - ACK 响应
    """

    pass  # 空数据模型


class ErrorData(CamelCaseModel):
    """错误数据载荷

    内部使用snake_case，序列化输出camelCase。
    """

    error_code: str
    error_message: str


class SubscriptionInfo(CamelCaseModel):
    """单个订阅信息

    注意：使用 interval 而非 resolution，以与数据库字段和API设计保持一致。
    内部使用snake_case，序列化输出camelCase。
    """

    subscription_key: str
    data_type: str
    exchange: str
    symbol: str
    interval: str | None = None  # 统一使用 interval
    product_type: str
    status: str
    subscribed_at: int
    message_count: int = 0
    last_message_at: int | None = None


class StrategyMetadataByTypeData(CamelCaseModel):
    """单个策略元数据包装模型

    用于 GET_STRATEGY_METADATA_BY_TYPE 响应。
    设计文档: 07-websocket-protocol.md

    格式:
    {
        "strategy": {
            "type": "...",
            "name": "...",
            ...
        }
    }
    """

    strategy: StrategyMetadataResponse
