"""
WebSocket数据载荷模型

定义WebSocket消息中的data字段载荷模型。

作者: Claude Code
版本: v2.0.0
"""

from typing import Any
from pydantic import BaseModel, Field

# 使用本地基类进行命名转换
from ..base import CamelCaseModel

# 从 trading 模块导入数据模型
from ..trading.quote_models import QuotesValue, QuotesData


# ==================== 数据载荷模型 ====================


class ConfigData(BaseModel):
    """
    配置数据载荷模型

    TradingView数据源配置信息。
    用于WebSocket响应的data字段载荷。
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
    symbols_types: list[dict[str, str]] = []  # 标的类型


class SearchSymbolsData(BaseModel):
    """
    搜索交易对数据载荷模型

    用于WebSocket响应的data字段载荷。
    """

    symbols: list[dict[str, str]]  # 交易对列表
    total: int  # 总数量
    count: int  # 当前返回数量


class ServerTimeData(BaseModel):
    """
    服务器时间数据载荷模型

    用于WebSocket响应的data字段载荷。
    """

    server_time: int  # 服务器时间
    timezone: str = "UTC"  # 时区


class SubscribeData(BaseModel):
    """
    订阅响应数据载荷模型

    用于WebSocket响应的data字段载荷。
    支持部分成功情况。
    """

    status: str = "success"  # 状态：success/partial
    subscriptions: list[str]  # 成功的订阅键列表（v2.0格式）
    failed: list[dict[str, Any]] | None = None  # 失败的订阅列表


class UnsubscribeData(BaseModel):
    """
    取消订阅响应数据载荷模型

    用于WebSocket响应的data字段载荷。
    """

    status: str = "success"  # 状态


class SubscriptionsData(BaseModel):
    """
    查询订阅响应数据载荷模型

    用于WebSocket响应的data字段载荷。
    """

    subscriptions: dict[str, list[dict[str, str]]]  # 订阅列表
    count: int  # 订阅数量


class MetricsData(BaseModel):
    """
    指标查询响应数据载荷模型

    用于WebSocket响应的data字段载荷。
    """

    metrics: dict[str, Any]  # 指标数据
    active_connections: int  # 活跃连接数
    subscription_count: int  # 订阅数量


# ==================== 错误和任务载荷 ====================


class ErrorData(CamelCaseModel):
    """错误数据载荷

    内部使用snake_case，序列化输出camelCase。
    """
    error_code: str
    error_message: str


class TaskResultData(CamelCaseModel):
    """任务完成响应数据载荷

    用于异步任务完成响应，包含任务类型和结果。
    遵循API设计文档v2.1规范：type字段在data内部。
    内部使用snake_case，序列化输出camelCase。
    """
    type: str = ""
    result: dict[str, Any] = Field(default_factory=dict)


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


# ==================== 导入需要的类型 ====================

from ..trading.kline_models import KlineBars
from ..trading.symbol_models import SymbolInfo

# ==================== 向后兼容性别名 ====================

# 响应数据别名
ConfigResponse = ConfigData
SearchSymbolsResponse = SearchSymbolsData
ResolveSymbolData = SymbolInfo
ResolveSymbolResponse = ResolveSymbolData
KlinesResponse = KlineBars
ServerTimeResponse = ServerTimeData
QuotesResponse = QuotesData
SubscriptionsResponse = SubscriptionsData
MetricsResponse = MetricsData

# 订阅相关别名
SubscribeResponse = SubscribeData
UnsubscribeResponse = UnsubscribeData
