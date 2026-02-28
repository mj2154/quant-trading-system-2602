"""
任务数据模型

对应数据库 tasks 表的 Pydantic 模型。

作者: Claude Code
版本: v2.0.0
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, Enum):
    """任务类型枚举"""

    # TradingView 数据任务
    TV_SUBSCRIBE_KLINE = "tv.subscribe_kline"
    TV_FETCH_HISTORY = "tv.fetch_history"
    TV_SEARCH_SYMBOLS = "tv.search_symbols"

    # 系统管理任务
    SYSTEM_FETCH_EXCHANGE_INFO = "system.fetch_exchange_info"
    SYSTEM_SYNC_SYMBOLS = "system.sync_symbols"

    # 第三方订阅任务
    THIRD_PARTY_WEBHOOK = "third_party.webhook"
    THIRD_PARTY_RSS_NEWS = "third_party.rss_news"

    # 兼容旧格式
    GET_KLINES = "get_klines"
    GET_SERVER_TIME = "get_server_time"
    GET_QUOTES = "get_quotes"
    GET_FUTURES_ACCOUNT = "get_futures_account"
    GET_SPOT_ACCOUNT = "get_spot_account"


# 任务分类映射（用于旧格式转换）
TASK_NAMESPACE_MAP: dict[str, str] = {
    # TV 任务
    "subscribe_kline": TaskType.TV_SUBSCRIBE_KLINE.value,
    "fetch_history": TaskType.TV_FETCH_HISTORY.value,
    "search_symbols": TaskType.TV_SEARCH_SYMBOLS.value,
    # 系统任务
    "fetch_exchange_info": TaskType.SYSTEM_FETCH_EXCHANGE_INFO.value,
    "sync_symbols": TaskType.SYSTEM_SYNC_SYMBOLS.value,
}


def convert_legacy_task_type(task_type: str) -> str:
    """将旧任务类型转换为新格式

    Args:
        task_type: 旧任务类型，如 "subscribe_kline"

    Returns:
        新任务类型，如 "tv.subscribe_kline"
    """
    return TASK_NAMESPACE_MAP.get(task_type, f"tv.{task_type}")


class UnifiedTaskPayload(BaseModel):
    """统一任务载荷 - 支持 TradingView 和系统管理任务

    用于存储在 tasks 表的 payload 字段中。

    Attributes:
        action: 任务动作，如 "tv.subscribe_kline", "system.fetch_exchange_info"
        resource: 资源标识，如 "BINANCE:BTCUSDT@KLINE_1"（可选）
        params: 额外参数字典

    Examples:
        >>> task = UnifiedTaskPayload(
        ...     action="system.fetch_exchange_info",
        ...     resource="BINANCE",
        ...     params={"mode": "all"}
        ... )
        >>> task.to_json()
        '{"action": "system.fetch_exchange_info", "resource": "BINANCE", "params": {"mode": "all"}}'

        >>> UnifiedTaskPayload.model_validate_json('{"action": "tv.subscribe_kline", "resource": "BINANCE:BTCUSDT"}')
        UnifiedTaskPayload(action='tv.subscribe_kline', resource='BINANCE:BTCUSDT', params={})
    """

    action: str = Field(..., description="任务动作，如 tv.subscribe_kline, system.fetch_exchange_info")
    resource: str = Field(default="", description="资源标识，如 BINANCE:BTCUSDT@KLINE_1")
    params: dict[str, Any] = Field(default_factory=dict, description="额外参数字典")

    @property
    def task_type(self) -> str:
        """获取任务类型（action 的别名，用于兼容旧接口）

        Returns:
            任务类型字符串
        """
        return self.action


class TaskCreate(BaseModel):
    """任务创建请求模型"""

    type: str = Field(..., description="任务类型")
    payload: dict[str, Any] = Field(default_factory=dict, description="任务参数字典")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "tv.subscribe_kline",
                "payload": {
                    "action": "tv.subscribe_kline",
                    "resource": "BINANCE:BTCUSDT@KLINE_1m",
                    "params": {}
                }
            }
        }
    )


class TaskResponse(BaseModel):
    """任务响应模型"""

    id: int = Field(..., description="任务ID")
    type: str = Field(..., description="任务类型")
    payload: dict[str, Any] = Field(..., description="任务参数")
    result: dict[str, Any] | None = Field(None, description="任务结果")
    status: TaskStatus = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class TaskUpdate(BaseModel):
    """任务更新请求模型"""

    status: TaskStatus | None = Field(None, description="任务状态")
    result: dict[str, Any] | None = Field(None, description="任务结果")


class TaskListResponse(BaseModel):
    """任务列表响应模型"""

    items: list[TaskResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
