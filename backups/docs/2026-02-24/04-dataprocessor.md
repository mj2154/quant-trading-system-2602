# DataProcessor 统一数据处理中心

## 1. 设计背景

API 服务需要监听多个数据库通知频道，包括任务完成通知、实时数据更新通知、信号通知等。为了统一管理这些监听，建立单一的数据库连接，API 服务设计 **DataProcessor** 作为对内的**统一数据处理中心**。

## 2. 核心职责

DataProcessor 是 API 服务内部的数据处理中枢，负责：

1. **建立统一的数据库连接**：使用单一 PostgreSQL LISTEN 连接监听所有通知频道
2. **接收数据库通知**：监听任务、订阅、实时数据、信号等各类数据库通知
3. **根据频道类型处理或转发**：不同频道采用不同处理策略
4. **推送数据给客户端**：通过 ClientManager 将数据推送给订阅的前端

## 3. 监听频道与处理策略

| 频道 | 触发条件 | 处理策略 |
|------|----------|----------|
| `task.completed` | 任务状态更新为 completed | 解析通知，查询 klines_history，推送结果给客户端 |
| `task.failed` | 任务状态更新为 failed | 推送错误消息给客户端 |
| `realtime.update` | realtime_data.data 更新 | 解析数据，广播给订阅该 subscription_key 的客户端 |
| `signal.new` | strategy_signals 插入新记录 | 广播给订阅对应 SIGNAL:{alert_id} 的客户端 |
| `config.new/update/delete` | strategy_config 变更 | 广播给订阅 strategy:* 的客户端 |
| `alert_config.new/update/delete` | alert_configs 变更 | 仅记录日志，前端通过 CRUD 响应更新状态 |

> **重要说明**：`subscription.add/remove/clean` 频道由币安服务监听，API 服务不需要监听这些频道。

## 4. 组件结构

```
DataProcessor
├── _on_notification()          # 业务事件处理 (signal.new, config.*, alert_config.*)
├── _on_task_notification()    # 任务事件处理 (task.completed, task.failed)
├── _on_subscription_notification()  # 订阅变更处理 (记录日志)
├── _on_realtime_notification() # 实时数据处理 (realtime.update)
└── _client_manager           # 客户端管理，用于推送数据
```

## 5. 任务处理流程

```
任务完成通知 (task.completed)
    │
    ▼
DataProcessor._on_task_notification()
    │
    ├── 解析通知：task_id, task_type, payload, result
    │
    ├── 通过 ClientManager.get_client_by_task(task_id) 找到客户端
    │
    ├── 根据 task_type 处理：
    │   ├── get_klines: 查询 klines_history 表获取数据
    │   ├── get_server_time: 直接使用 result
    │   └── get_quotes: 直接使用 result
    │
    └── 通过 ClientManager.send() 推送结果给客户端
```

## 6. 任务结果处理

| 任务类型 | result 来源 | 数据库查询 | 推送内容 |
|---------|------------|-----------|----------|
| `get_klines` | 通知中为 NULL | 查询 klines_history | 从 klines_history 查询完整数据 |
| `get_server_time` | 通知中已包含 | 无需查询 | 直接推送 result |
| `get_quotes` | 通知中已包含 | 无需查询 | 直接推送 result |
| 失败任务 | 通知中包含 | 无需查询 | 推送错误消息 |

## 7. 实时数据处理

```python
async def _on_realtime_notification(self, payload: dict) -> None:
    """处理实时数据更新通知"""
    subscription_key = payload["subscription_key"]
    data = payload["data"]
    data_type = payload["data_type"]

    # 广播给订阅该 subscription_key 的所有客户端
    await self._client_manager.broadcast_by_key(subscription_key, {
        "action": "update",
        "data": {
            "type": data_type,
            "subscription_key": subscription_key,
            "data": data
        }
    })
```

## 8. 信号处理

```python
async def _on_signal_notification(self, payload: dict) -> None:
    """处理新信号通知"""
    alert_id = payload["alert_id"]
    signal_value = payload["signal_value"]
    symbol = payload["symbol"]

    # 广播给订阅该 SIGNAL:{alert_id} 的客户端
    await self._client_manager.broadcast_by_key(f"SIGNAL:{alert_id}", {
        "action": "signal",
        "data": {
            "alert_id": alert_id,
            "symbol": symbol,
            "signal_value": signal_value
        }
    })
```

## 9. 与其他组件的关系

| 组件 | 关系 |
|------|------|
| **TaskRouter** | TaskRouter 创建任务并注册 task_id -> client_id 映射 |
| **ClientManager** | DataProcessor 使用 ClientManager 推送数据 |
| **SubscriptionManager** | DataProcessor 使用 SubscriptionManager 获取订阅者列表 |
| **TaskResultHandler** | **已移除**，功能合并到 DataProcessor |

## 10. 实现示例

### 10.1 DataProcessor 类

```python
class DataProcessor:
    """统一数据处理中心"""

    def __init__(
        self,
        pool: asyncpg.Pool,
        client_manager: ClientManager,
        subscription_manager: SubscriptionManager,
    ):
        self._pool = pool
        self._client_manager = client_manager
        self._subscription_manager = subscription_manager
        self._listeners: dict[str, asyncio.Queue] = {}

    async def start(self) -> None:
        """启动监听"""
        # 注册通知频道
        channels = [
            "task.completed",
            "task.failed",
            "realtime.update",
            "signal.new",
            "config.new",
            "config.update",
            "config.delete",
        ]

        for channel in channels:
            await self._pool.add_listener(channel, self._handle_notification)

    async def _handle_notification(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        """处理数据库通知"""
        try:
            data = json.loads(payload)

            if channel == "task.completed":
                await self._on_task_notification(data)
            elif channel == "task.failed":
                await self._on_task_failed(data)
            elif channel == "realtime.update":
                await self._on_realtime_notification(data)
            elif channel == "signal.new":
                await self._on_signal_notification(data)
            elif channel.startswith("config."):
                await self._on_config_notification(channel, data)
            elif channel.startswith("alert_config."):
                await self._on_alert_config_notification(channel, data)
        except Exception as e:
            logger.error(f"处理通知失败: {e}")

    async def _on_task_notification(self, payload: dict) -> None:
        """处理任务完成通知"""
        task_id = payload["data"]["id"]
        task_type = payload["data"]["type"]
        task_payload = payload["data"].get("payload", {})
        result = payload["data"].get("result")

        # 找到客户端
        client_id = self._client_manager.get_client_by_task(task_id)
        if not client_id:
            logger.warning(f"未找到任务 {task_id} 对应的客户端")
            return

        # 根据任务类型处理
        if task_type == "get_klines":
            # 查询 klines_history 获取数据
            klines = await self._query_klines_history(task_payload)
            response = {
                "action": "success",
                "data": {
                    "type": "klines",
                    "klines": klines,
                    "count": len(klines)
                }
            }
        else:
            # 直接使用 result
            response = {
                "action": "success",
                "data": result
            }

        # 推送结果
        await self._client_manager.send(client_id, response)

    async def _on_realtime_notification(self, payload: dict) -> None:
        """处理实时数据更新"""
        subscription_key = payload["data"]["subscription_key"]
        data = payload["data"]["data"]
        data_type = payload["data"]["data_type"]

        # 广播给订阅该 key 的所有客户端
        await self._client_manager.broadcast_by_key(
            subscription_key,
            {
                "action": "update",
                "data": {
                    "type": data_type,
                    "subscription_key": subscription_key,
                    "data": data
                }
            }
        )

    async def _on_signal_notification(self, payload: dict) -> None:
        """处理新信号通知"""
        alert_id = payload["data"]["alert_id"]
        signal_value = payload["data"]["signal_value"]
        symbol = payload["data"]["symbol"]

        # 广播给订阅该 SIGNAL:{alert_id} 的客户端
        await self._client_manager.broadcast_by_key(
            f"SIGNAL:{alert_id}",
            {
                "action": "signal",
                "data": {
                    "alert_id": alert_id,
                    "symbol": symbol,
                    "signal_value": signal_value
                }
            }
        )
```

### 10.2 初始化

```python
# main.py
async def main():
    # 初始化组件
    pool = await create_pool(...)
    client_manager = ClientManager()
    subscription_manager = SubscriptionManager(...)
    tasks_repository = TasksRepository(pool)
    realtime_repository = RealtimeDataRepository(pool)

    # 初始化 DataProcessor
    data_processor = DataProcessor(
        pool=pool,
        client_manager=client_manager,
        subscription_manager=subscription_manager,
    )

    # 初始化 TaskRouter
    task_router = TaskRouter(
        tasks_repository=tasks_repository,
        client_manager=client_manager,
    )

    # 启动
    await data_processor.start()

    # 启动 API 服务
    app = create_app(...)
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 11. 设计优势

| 优势 | 说明 |
|------|------|
| **单一连接** | 所有通知监听使用一个数据库连接，减少资源消耗 |
| **统一管理** | 所有对内数据处理集中在一处，便于维护和调试 |
| **职责清晰** | DataProcessor 只负责接收和推送，不处理业务逻辑 |
| **消除重复** | 避免多个组件重复监听同一频道 |

## 12. 相关文件

| 文件 | 说明 |
|------|------|
| `services/api-service/src/gateway/data_processor.py` | DataProcessor 实现 |
| `services/api-service/src/gateway/task_router.py` | 任务路由器 |
| `services/api-service/src/gateway/client_manager.py` | 客户端管理 |
| `services/api-service/src/gateway/subscription_manager.py` | 订阅管理器 |

## 相关文档

- [QUANT_TRADING_SYSTEM_ARCHITECTURE.md](./QUANT_TRADING_SYSTEM_ARCHITECTURE.md) - 完整实施文档
- [01-task-subscription.md](./01-task-subscription.md) - 任务与订阅管理
- [02-dataflow.md](./02-dataflow.md) - 数据流设计
- [03-kline-collector.md](./03-kline-collector.md) - K线采集设计

---

**版本**：v1.0
**更新**：2026-02-21
