"""
WebSocket 消息模型

用于构建 WebSocket 请求消息，确保类型安全和一致性。
"""

from pydantic import BaseModel
from typing import Literal


class WSRequest(BaseModel):
    """WebSocket 请求基类"""

    method: Literal["SUBSCRIBE", "UNSUBSCRIBE"]
    params: list[str]
    id: int


class WSSubscribeRequest(WSRequest):
    """订阅请求"""

    method: Literal["SUBSCRIBE"] = "SUBSCRIBE"


class WSUnsubscribeRequest(WSRequest):
    """取消订阅请求"""

    method: Literal["UNSUBSCRIBE"] = "UNSUBSCRIBE"
