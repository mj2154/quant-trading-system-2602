"""
统一任务载荷模型

支持 TradingView 和系统管理任务的统一任务格式。

设计原则：
- action: 任务大类（tv, system, third_party）
- resource: 资源类型（symbol, interval, exchange 等，可选）
- params: 任意参数（JSON 灵活扩展）

注意：此文件与 shared/python/models/task.py 实现相同，
      由于跨服务引用不便，在此重复定义。
"""

from dataclasses import dataclass, field
import json
from typing import Any


@dataclass
class UnifiedTaskPayload:
    """统一任务载荷 - 支持 TradingView 和系统管理任务

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

        >>> UnifiedTaskPayload.from_json('{"action": "tv.subscribe_kline", "resource": "BINANCE:BTCUSDT"}')
        UnifiedTaskPayload(action='tv.subscribe_kline', resource='BINANCE:BTCUSDT', params={})
    """

    action: str  # 任务动作: tv.subscribe_kline, system.fetch_exchange_info
    resource: str = ""  # 资源标识: BINANCE:BTCUSDT@KLINE_1（可选）
    params: dict[str, Any] = field(default_factory=dict)  # 额外参数

    @classmethod
    def from_json(cls, data: str) -> "UnifiedTaskPayload":
        """从 JSON 字符串解析

        Args:
            data: JSON 格式字符串

        Returns:
            UnifiedTaskPayload 实例

        Raises:
            json.JSONDecodeError: JSON 格式无效
        """
        obj = json.loads(data)
        return cls(
            action=obj.get("action", ""),
            resource=obj.get("resource", ""),
            params=obj.get("params", {}),
        )

    def to_json(self) -> str:
        """序列化为 JSON 字符串

        Returns:
            JSON 格式字符串
        """
        return json.dumps(
            {
                "action": self.action,
                "resource": self.resource,
                "params": self.params,
            }
        )

    @property
    def task_type(self) -> str:
        """获取任务类型（action 的别名，用于兼容旧接口）

        Returns:
            任务类型字符串
        """
        return self.action


# 任务类型常量
class TaskActions:
    """任务动作常量"""

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


# 任务分类映射（旧格式到新格式）
LEGACY_TO_NEW_TASK_TYPE = {
    # TV 任务
    "subscribe_kline": TaskActions.TV_SUBSCRIBE_KLINE,
    "fetch_history": TaskActions.TV_FETCH_HISTORY,
    "search_symbols": TaskActions.TV_SEARCH_SYMBOLS,
    # 系统任务
    "sync_exchange_info": TaskActions.SYSTEM_FETCH_EXCHANGE_INFO,
    "fetch_exchange_info": TaskActions.SYSTEM_FETCH_EXCHANGE_INFO,
    "sync_symbols": TaskActions.SYSTEM_SYNC_SYMBOLS,
}


def convert_legacy_task_type(task_type: str) -> str:
    """将旧任务类型转换为新格式

    Args:
        task_type: 旧任务类型，如 "subscribe_kline"

    Returns:
        新任务类型，如 "tv.subscribe_kline"
    """
    return LEGACY_TO_NEW_TASK_TYPE.get(task_type, f"tv.{task_type}")
