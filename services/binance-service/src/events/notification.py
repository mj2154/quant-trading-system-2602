"""
数据库通知类型定义

定义任务队列和订阅相关的通知类型。
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass
import json


class EventType(str, Enum):
    """数据库通知事件类型"""

    # 任务相关
    TASK_SUBSCRIBE = "task.subscribe"  # 新任务订阅
    TASK_COMPLETE = "task.complete"   # 任务完成
    TASK_FAIL = "task.fail"           # 任务失败

    # K线相关
    KLINE_NEW = "kline.new"          # 新K线数据
    KLINE_CLOSED = "kline.closed"     # K线收盘

    # 信号相关
    SIGNAL_NEW = "signal.new"         # 新信号


@dataclass
class TaskPayload:
    """任务载荷（旧格式，兼容保留）

    Attributes:
        task_type: 任务类型，如 "subscribe_kline", "fetch_history"
        symbol: 交易对符号
        interval: K线间隔
        task_id: 任务ID（从通知载荷的 row_to_json(NEW).id 提取）
        payload: 额外参数（JSON字符串）
    """

    task_type: str
    symbol: str
    interval: str
    task_id: Optional[int] = None
    payload: Optional[str] = None

    @classmethod
    def from_json(cls, data: str) -> "TaskPayload":
        """从JSON字符串解析"""
        obj = json.loads(data)
        return cls(
            task_type=obj.get("task_type", ""),
            symbol=obj.get("symbol", ""),
            interval=obj.get("interval", ""),
            task_id=obj.get("id"),  # 从通知载荷提取 id
            payload=obj.get("payload"),
        )

    def to_json(self) -> str:
        """序列化为JSON字符串"""
        data = {
            "task_type": self.task_type,
            "symbol": self.symbol,
            "interval": self.interval,
            "payload": self.payload,
        }
        if self.task_id is not None:
            data["id"] = self.task_id
        return json.dumps(data)
