"""
账户信息模型

对应数据库 account_info 表的 Pydantic 模型。
包括账户创建、响应等模型。

设计文档: 01-task-subscription.md - account_info 账户信息表

作者: Claude Code
版本: v2.0.0
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class AccountInfoCreate(BaseModel):
    """账户信息创建请求模型

    对应数据库 account_info 表的 id, account_type, data 字段。
    """

    account_type: str = Field(
        ...,
        description="账户类型: SPOT(现货), FUTURES(期货)"
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="账户原始数据（JSON格式存储）"
    )


class AccountInfoUpdate(BaseModel):
    """账户信息更新请求模型"""

    data: dict[str, Any] | None = Field(None, description="账户原始数据")


class AccountInfoResponse(BaseModel):
    """账户信息响应模型

    对应数据库 account_info 表的所有字段：
    - id: 记录ID
    - account_type: 账户类型 (SPOT/FUTURES)
    - data: 账户原始数据 (JSONB)
    - update_time: 币安返回的更新时间
    - created_at: 创建时间
    - updated_at: 更新时间
    """

    id: int = Field(..., description="账户ID")
    account_type: str = Field(..., description="账户类型: SPOT/FUTURES")
    data: dict[str, Any] = Field(..., description="账户原始数据")
    update_time: int | None = Field(None, description="币安返回的更新时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class AccountInfoListResponse(BaseModel):
    """账户信息列表响应模型"""

    items: list[AccountInfoResponse] = Field(..., description="账户列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")


# 现货账户信息（从 data 字段解析的视图模型，非数据库映射）
class SpotAccountInfo(BaseModel):
    """现货账户详细信息"""

    account_type: str = "SPOT"
    exchange: str = "BINANCE"
    total_asset: float = Field(default=0.0, description="总资产(USDT)")
    total_btc: float = Field(default=0.0, description="总资产(BTC)")
    balances: list[dict[str, Any]] = Field(default_factory=list, description="余额列表")

    def __str__(self) -> str:
        return f"SpotAccountInfo(total_btc={self.total_btc})"


# 期货账户信息（从 data 字段解析的视图模型，非数据库映射）
class FuturesAccountInfo(BaseModel):
    """期货账户详细信息"""

    account_type: str = "FUTURES"
    exchange: str = "BINANCE"
    total_balance: float = Field(default=0.0, description="总余额")
    total_asset: float = Field(default=0.0, description="总资产(USDT)")
    available_balance: float = Field(default=0.0, description="可用余额")
    total_position_value: float = Field(default=0.0, description="持仓市值")
    total_unrealized_pnl: float = Field(default=0.0, description="未实现盈亏")
    margin_balance: float = Field(default=0.0, description="保证金余额")
    positions: list[dict[str, Any]] = Field(default_factory=list, description="持仓列表")

    def __str__(self) -> str:
        return f"FuturesAccountInfo(balance={self.total_balance}, pnl={self.total_unrealized_pnl})"


# 账户余额模型
class AccountBalance(BaseModel):
    """账户余额模型"""

    asset: str = Field(..., description="资产名称")
    free: float = Field(default=0.0, description="可用数量")
    locked: float = Field(default=0.0, description="冻结数量")

    @property
    def total(self) -> float:
        """总数量"""
        return self.free + self.locked

    def __str__(self) -> str:
        return f"{self.asset}: {self.free} free, {self.locked} locked"


# 持仓信息模型
class PositionInfo(BaseModel):
    """持仓信息模型"""

    symbol: str = Field(..., description="交易对")
    position_side: str = Field(default="BOTH", description="持仓方向: LONG, SHORT, BOTH")
    position_amount: float = Field(default=0.0, description="持仓数量")
    entry_price: float = Field(default=0.0, description="开仓价格")
    mark_price: float = Field(default=0.0, description="标记价格")
    unrealized_pnl: float = Field(default=0.0, description="未实现盈亏")
    leverage: int = Field(default=1, description="杠杆倍数")
    margin: float = Field(default=0.0, description="保证金")

    @property
    def pnl_percent(self) -> float:
        """盈亏百分比"""
        if self.margin == 0:
            return 0.0
        return (self.unrealized_pnl / self.margin) * 100

    def __str__(self) -> str:
        return f"{self.symbol} {self.position_side}: {self.position_amount} @ {self.entry_price}"
