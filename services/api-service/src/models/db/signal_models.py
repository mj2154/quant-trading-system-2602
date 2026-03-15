"""
信号数据模型

仅保留启用/禁用响应模型。
API 服务只负责告警配置管理，信号由 signal-service 处理。

作者: Claude Code
版本: v3.0.0
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from ..base import CamelCaseModel


class StrategyParam(CamelCaseModel):
    """策略参数定义"""

    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型")
    default: int | float | bool = Field(..., description="默认值")
    min: int | float | None = Field(None, description="最小值")
    max: int | float | None = Field(None, description="最大值")
    description: str = Field(..., description="参数描述")


class StrategyMetadataResponse(CamelCaseModel):
    """策略元数据响应模型 - 序列化时自动转为 camelCase

    用于 GET_STRATEGY_METADATA 响应，自动将所有字段转换为 camelCase。
    与设计文档保持一致: docs/backend/design/07-websocket-protocol.md
    """

    type: str = Field(..., description="策略类型（类名）")
    name: str = Field(..., description="策略显示名称")
    description: str = Field(..., description="策略描述")
    params: list[StrategyParam] = Field(
        default_factory=list, description="策略参数列表"
    )
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")


class StrategyMetadataListResponse(CamelCaseModel):
    """策略元数据列表响应模型 - 序列化时自动转为 camelCase"""

    strategies: list[StrategyMetadataResponse] = Field(
        ..., description="策略元数据列表"
    )


class SignalRecordResponse(CamelCaseModel):
    """信号记录响应模型 - 序列化时自动转为 camelCase

    用于 LIST_SIGNALS 响应，自动将所有字段转换为 camelCase。
    与设计文档保持一致: docs/backend/design/07-websocket-protocol.md
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
    computed_at: datetime = Field(..., description="信号计算时间")
    source_subscription_key: str | None = Field(None, description="触发该信号的订阅键")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")
    created_by: str | None = Field(None, description="创建者标识")


class SignalListResponse(CamelCaseModel):
    """信号列表响应模型 - 序列化时自动转为 camelCase"""

    items: list[SignalRecordResponse] = Field(..., description="信号记录列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")


class EnableDisableResponse(CamelCaseModel):
    """启用/禁用响应模型

    使用 CamelCaseModel 基类，序列化时自动将字段转换为 camelCase。
    """

    id: UUID = Field(..., description="配置ID")
    name: str = Field(..., description="名称")
    is_enabled: bool = Field(..., description="是否启用")
    message: str = Field(..., description="操作结果消息")
