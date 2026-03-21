"""
WebSocket 消息模型

用于构造币安 WebSocket 订阅/取消订阅请求，以及解析响应。

文档来源:
- binance_futures_docs/01_U本位合约/02_Websocket行情推送/WEB_SOCKET_API.md
- binance_spot_docs/01_WebSocket API/Response format.md
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .base import CamelCaseModel, SnakeCaseModel


class WSSubscribeRequest(CamelCaseModel):
    """WebSocket 订阅请求模型

    币安 WebSocket 协议格式：
    {
        "method": "SUBSCRIBE",
        "params": ["btcusdt@kline_1m", "btcusdt@ticker"],
        "id": 1
    }
    """

    method: str = Field(default="SUBSCRIBE", description="请求方法")
    params: list[str] = Field(description="订阅的流名称列表")
    id: int = Field(description="请求 ID")


class WSUnsubscribeRequest(CamelCaseModel):
    """WebSocket 取消订阅请求模型

    币安 WebSocket 协议格式：
    {
        "method": "UNSUBSCRIBE",
        "params": ["btcusdt@kline_1m", "btcusdt@ticker"],
        "id": 1
    }
    """

    method: str = Field(default="UNSUBSCRIBE", description="请求方法")
    params: list[str] = Field(description="取消订阅的流名称列表")
    id: int = Field(description="请求 ID")


class WSResponse(SnakeCaseModel):
    """WebSocket 通用响应模型

    用于解析所有币安 WebSocket API 的响应。

    成功响应: status=200, result有值, error=None
    失败响应: status!=200, result=None, error有值

    文档来源:
    - binance_spot_docs/01_WebSocket API/Response format.md
    - binance_futures_docs/01_U本位合约/02_交易接口/03_WebSocket API/下单(TRADE).md
    """

    id: int | str = Field(description="请求 ID，与请求中的 id 对应")
    status: int = Field(alias="status", description="响应状态码 (200=成功, 400=失败)")
    result: dict[str, Any] | list[Any] | None = Field(
        default=None, alias="result", description="成功时的结果数据"
    )
    error: dict[str, Any] | None = Field(default=None, alias="error", description="失败时的错误信息")
    rate_limits: list[dict[str, Any]] | None = Field(
        default=None, alias="rateLimits", description="速率限制信息"
    )

    model_config = ConfigDict(populate_by_name=True)
