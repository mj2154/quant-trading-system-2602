"""
Gateway 模块

提供 WebSocket 客户端管理、任务路由、数据库通知监听、订阅管理等功能。

核心组件：
- DataProcessor: 统一数据处理中心，监听数据库通知并推送给客户端
- ClientManager: WebSocket 客户端管理
- SubscriptionManager: 订阅管理
- TaskRouter: 请求路由和任务创建
"""

from .alert_handler import AlertHandler
from .client_manager import ClientManager
from .data_processor import DataProcessor
from .subscription_manager import SubscriptionManager
from .task_router import TaskRouter
from .websocket_handler import ws_market

__all__ = [
    "ClientManager",
    "ws_market",
    "TaskRouter",
    "DataProcessor",
    "SubscriptionManager",
    "AlertHandler",
]
