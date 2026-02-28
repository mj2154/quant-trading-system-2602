"""
实时数据模型

对应数据库 realtime_data 表的 Pydantic 模型。
包括订阅相关的所有数据模型。

作者: Claude Code
版本: v2.0.0
"""

from typing import Any
from pydantic import BaseModel, Field


class SubscriptionKey(BaseModel):
    """
    订阅键

    用于唯一标识一个订阅。
    格式: EXCHANGE:SYMBOL@TYPE_INTERVAL
    注意：内部使用 interval 字段，与数据库字段和API设计保持一致。
    """

    exchange: str  # 交易所代码
    symbol: str  # 交易对
    subscription_type: str  # 订阅类型
    interval: str | None = None  # K线周期（可选）

    def __str__(self) -> str:
        if self.interval:
            return f"{self.exchange}:{self.symbol}@{self.subscription_type}_{self.interval}"
        return f"{self.exchange}:{self.symbol}@{self.subscription_type}"

    def to_key(self) -> str:
        """转换为字符串键"""
        return self.__str__()

    def __hash__(self) -> int:
        """使 SubscriptionKey 可以作为字典的键"""
        return hash((self.exchange, self.symbol, self.subscription_type, self.interval))

    def __eq__(self, other) -> bool:
        """支持相等性比较"""
        if not isinstance(other, SubscriptionKey):
            return False
        return (
            self.exchange == other.exchange
            and self.symbol == other.symbol
            and self.subscription_type == other.subscription_type
            and self.interval == other.interval
        )

    @classmethod
    def create_key(cls, symbol: str, subscription_type: str, params: dict | None = None) -> str:
        """
        创建订阅键

        Args:
            symbol: 交易对名称
            subscription_type: 订阅类型
            params: 额外参数（支持 interval 字段）

        Returns:
            str: 订阅键
        """
        # 解析symbol以获取交易所和交易对
        if ":" in symbol:
            exchange, symbol_part = symbol.split(":", 1)
        else:
            exchange, symbol_part = "UNKNOWN", symbol

        interval = None
        if params:
            interval = params.get("interval")

        # 构建键
        key_obj = cls(
            exchange=exchange.upper(),
            symbol=symbol_part.upper(),
            subscription_type=subscription_type.upper(),
            interval=interval,
        )

        return key_obj.to_key()

    @classmethod
    def from_key(cls, key: str) -> "SubscriptionKey":
        """从字符串键创建实例"""
        if "@" not in key:
            raise ValueError(f"无效的订阅键格式: {key}")

        exchange_symbol, type_part = key.rsplit("@", 1)
        if ":" not in exchange_symbol:
            raise ValueError(f"无效的交易所和符号格式: {exchange_symbol}")

        exchange, symbol = exchange_symbol.split(":", 1)

        if "_" in type_part:
            subscription_type, interval = type_part.rsplit("_", 1)
        else:
            subscription_type, interval = type_part, None

        return cls(
            exchange=exchange.upper(),
            symbol=symbol.upper(),
            subscription_type=subscription_type.upper(),
            interval=interval,
        )


class SubscriptionInfo(BaseModel):
    """
    订阅信息

    包含订阅的详细信息。
    """

    client_id: str  # 客户端ID
    subscription_key: SubscriptionKey  # 订阅键
    symbol: str  # 交易对
    subscription_type: str  # 订阅类型
    interval: str | None = None  # K线周期（可选）
    created_at: float  # 创建时间
    last_updated: float  # 最后更新时间

    def __str__(self) -> str:
        return f"SubscriptionInfo({self.client_id}, {self.subscription_key})"


class ClientSubscriptions(BaseModel):
    """
    客户端订阅

    记录一个客户端的所有订阅。
    """

    client_id: str  # 客户端ID
    subscriptions: set[str]  # 订阅键集合
    created_at: float  # 创建时间
    last_activity: float  # 最后活动时间

    def __str__(self) -> str:
        return f"ClientSubscriptions({self.client_id}, {len(self.subscriptions)} subs)"


class ExchangeSubscriptions(BaseModel):
    """
    交易所订阅

    记录一个交易所所需维护的订阅。
    """

    exchange: str  # 交易所代码
    streams: set[str]  # 订阅流集合
    created_at: float  # 创建时间
    last_updated: float  # 最后更新时间

    def __str__(self) -> str:
        return f"ExchangeSubscriptions({self.exchange}, {len(self.streams)} streams)"


class SubscriptionChange(BaseModel):
    """
    订阅变更

    记录订阅的变更信息。
    """

    exchange: str  # 交易所代码
    subscribe: list[str]  # 新增的订阅
    unsubscribe: list[str]  # 移除的订阅
    total_required: int  # 总的所需订阅数
    timestamp: float  # 变更时间

    def __str__(self) -> str:
        return (
            f"SubscriptionChange({self.exchange}, +{len(self.subscribe)}, -{len(self.unsubscribe)})"
        )


class SubscriptionStats(BaseModel):
    """
    订阅统计

    包含订阅的统计信息。
    """

    total_subscriptions: int  # 总订阅数
    unique_symbols: int  # 唯一交易对数
    subscriptions_by_type: dict[str, int]  # 按类型分组的订阅数
    subscriptions_by_exchange: dict[str, int]  # 按交易所分组的订阅数
    active_clients: int  # 活跃客户端数

    def __str__(self) -> str:
        return f"SubscriptionStats(total={self.total_subscriptions}, clients={self.active_clients})"


class ProductTypeInfo(BaseModel):
    """
    产品类型信息

    用于解析语义化交易对的产品类型。
    """

    type: str  # 产品类型
    base_symbol: str  # 基础货币
    quote_symbol: str  # 计价货币
    exchange_symbol: str  # 交易所中的符号
    api_endpoint: str  # API端点
    ws_stream: str  # WebSocket流名称
    is_perpetual: bool = False  # 是否是永续合约
    is_futures: bool = False  # 是否是期货
    expiry: str | None = None  # 交割日期（期货）

    def __str__(self) -> str:
        return f"ProductTypeInfo(type={self.type}, symbol={self.exchange_symbol})"


class SubscriptionRequest(BaseModel):
    """
    订阅请求项

    用于单个订阅请求。
    """

    symbol: str  # 交易对
    interval: str | None = None  # K线周期（可选）

    def __str__(self) -> str:
        if self.interval:
            return f"{self.symbol}@{self.interval}"
        return self.symbol


class SubscriptionBatch(BaseModel):
    """
    批量订阅

    用于批量处理订阅请求。
    """

    client_id: str  # 客户端ID
    subscriptions: dict[str, list[SubscriptionRequest]]  # 订阅列表
    timestamp: float  # 请求时间

    def __str__(self) -> str:
        return f"SubscriptionBatch({self.client_id}, {len(self.subscriptions)} types)"


class SubscriptionValidation(BaseModel):
    """
    订阅验证

    用于验证订阅请求。
    """

    is_valid: bool  # 是否有效
    errors: list[str]  # 错误列表
    warnings: list[str]  # 警告列表

    def __str__(self) -> str:
        if self.is_valid:
            return "SubscriptionValidation(valid=True)"
        return f"SubscriptionValidation(valid=False, errors={self.errors})"


class BatchSubscriptionResult(BaseModel):
    """
    批量订阅结果

    用于返回批量订阅处理的结果。
    """

    successful_subscriptions: dict[str, list[dict]]  # 成功的订阅
    failed: list[dict] | None = None  # 失败的订阅

    def __str__(self) -> str:
        total_success = sum(len(subs) for subs in self.successful_subscriptions.values())
        total_failed = len(self.failed) if self.failed else 0
        return f"BatchSubscriptionResult(success={total_success}, failed={total_failed})"
