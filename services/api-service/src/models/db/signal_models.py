"""
信号数据模型

仅保留启用/禁用响应模型。
API 服务只负责告警配置管理，信号由 signal-service 处理。

作者: Claude Code
版本: v3.0.0
"""

from uuid import UUID

from pydantic import BaseModel, Field


class EnableDisableResponse(BaseModel):
    """启用/禁用响应模型"""

    id: UUID = Field(..., description="配置ID")
    name: str = Field(..., description="名称")
    is_enabled: bool = Field(..., description="是否启用")
    message: str = Field(..., description="操作结果消息")
