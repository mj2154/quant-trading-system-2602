# 订单任务表设计

## 1. 设计目标

- **权威数据源**：订单状态以交易所为准，本地不维护"当前状态"
- **任务驱动**：订单操作通过任务表执行，复用现有 `tasks` 表结构
- **状态获取**：通过 WebSocket 订阅或任务查询获取最新状态
- **简化逻辑**：任务表只记录操作，不维护订单状态，避免状态不一致
- **数据保留**：订单记录永久保留，用于分析和追溯

## 2. 设计理念

### 2.1 为什么不再存储"当前状态"

| 问题 | 说明 |
|------|------|
| 状态不一致 | 网络问题会导致本地状态与交易所实际状态不统一 |
| 缺乏权威 | 交易所才是订单状态的唯一权威来源 |
| 维护复杂 | 需要处理各种边界情况（超时、重试等） |
| 生产风险 | 状态同步失败难以追溯真实状态 |

### 2.2 订单状态获取方式

```
┌─────────────────────────────────────────────────────────────────┐
│ 订单状态获取流程                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  方式A：WebSocket订阅（主推）                                    │
│    币安WS → ORDER_TRADE_UPDATE → 实时推送 → 前端               │
│                                                                 │
│  方式B：任务查询（兜底）                                         │
│    前端请求 → order_tasks 查询 → binance-service API查询       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**核心原则**：始终以交易所返回的状态为准，本地仅缓存用于展示。

### 2.3 复用 tasks 表结构

采用与 `tasks` 表相同的结构，复用代码逻辑：
- 仅 `type` 改为 `order.create`、`order.cancel`、`order.query`
- 独立表可设置不同的保留策略（订单永久保留）
- 其他字段完全兼容

## 3. 表结构

> **重要**: order_tasks 是 tasks 表的扩展，增加了 request_id 顶层字段。

### 3.1 tasks 表结构（基础任务表）

```sql
-- -----------------------------------------------------------------------------
-- tasks 基础任务表
-- 设计: 存储通用任务，request_id 提升到顶层便于查询
-- 参考文档: docs/backend/design/01-task-subscription.md
-- -----------------------------------------------------------------------------
CREATE TABLE tasks (
    id BIGSERIAL PRIMARY KEY,

    -- 任务类型: get_klines, get_server_time, get_quotes, system.fetch_exchange_info
    type VARCHAR(50) NOT NULL,

    -- 请求ID（前端生成，用于关联请求和响应）
    -- 提升到顶层字段，可建索引优化查询
    request_id VARCHAR(50),

    -- 任务参数（JSON格式）
    payload JSONB NOT NULL DEFAULT '{}',

    -- 任务结果（币安服务填写）
    result JSONB,

    -- 任务状态: pending, processing, completed, failed
    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks (type);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_request_id ON tasks (request_id);  -- 新增：request_id 索引

-- 转换为 Hypertable
SELECT create_hypertable('tasks', 'created_at');
```

### 3.2 order_tasks 表结构（订单任务表）

```sql
-- -----------------------------------------------------------------------------
-- order_tasks 订单任务表
-- 设计: 存储订单操作任务，复用 tasks 表结构并扩展
-- INSERT 触发 order_task_new 通知
-- UPDATE 触发 order_task_completed / order_task_failed 通知
-- 数据保留: 永久保留（用于分析和追溯）
-- 参考文档: docs/backend/design/04-trading-orders.md
-- -----------------------------------------------------------------------------
CREATE TABLE order_tasks (
    id BIGSERIAL,

    -- 任务类型
    type VARCHAR(50) NOT NULL,
    -- order.create - 创建订单
    -- order.cancel - 取消订单
    -- order.query  - 查询订单状态

    -- 请求ID（前端生成，用于关联请求和响应）
    -- 提升到顶层字段，可建索引优化查询
    -- 贯穿整个数据流：前端 → API → 币安 → 结果推送
    request_id VARCHAR(50),

    -- 任务参数（JSON格式）
    -- 注意：不再包含 requestId，从顶层字段获取
    -- order.create: {symbol, side, type, quantity, price, timeInForce, clientOrderId, marketType, ...}
    -- order.cancel: {symbol, orderId, clientOrderId}
    -- order.query:  {symbol, orderId, clientOrderId}
    payload JSONB NOT NULL DEFAULT '{}',

    -- 任务结果（API响应或错误信息）
    -- 成功: {orderId, status, ...}
    -- 失败: {code: -1013, msg: "Invalid quantity."}
    result JSONB,

    -- 任务状态
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending    - 等待处理
    -- processing - 处理中
    -- completed  - 已完成
    -- failed    - 失败

    -- 时间戳（必须是 NOT NULL 才能转换为 Hypertable）
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 转换为 Hypertable（必须在添加主键之前执行）
SELECT create_hypertable('order_tasks', 'created_at');

-- 添加复合主键（与 tasks 表一致，包含 created_at）
ALTER TABLE order_tasks ADD PRIMARY KEY (id, created_at);

-- 索引
CREATE INDEX IF NOT EXISTS idx_order_tasks_status ON order_tasks (status);
CREATE INDEX IF NOT EXISTS idx_order_tasks_type ON order_tasks (type);
CREATE INDEX IF NOT EXISTS idx_order_tasks_request_id ON order_tasks (request_id);  -- 新增：request_id 索引

-- 复合索引
CREATE INDEX IF NOT EXISTS idx_order_tasks_type_status ON order_tasks (type, status);
```

## 4. 字段说明

### 4.1 type 任务类型

| 类型 | 说明 | 触发方式 |
|------|------|----------|
| `order.create` | 创建订单 | 前端请求 |
| `order.cancel` | 取消订单 | 前端请求 |
| `order.query` | 查询订单状态 | 前端请求 / 定时任务 |

### 4.2 request_id 请求ID（重要）

> **设计决策**: `request_id` 从 payload 提升到顶层字段，原因：
> 1. **贯穿整个数据流**: 前端生成 → API写入 → 币安API调用 → 结果推送
> 2. **可建索引优化**: 顶层字段可建索引，查询效率高
> 3. **语义更清晰**: 顶层字段表示"请求身份"，payload 表示"请求参数"
> 4. **与 tasks 表统一**: 保持两张表结构一致

| 字段 | 类型 | 说明 |
|------|------|------|
| `request_id` | VARCHAR(50) | 请求ID（前端生成，格式: req_xxx，用于关联 ack/response） |

**数据流示例**:
```
1. 前端生成 request_id: "req_a1b2c3d4e5f6g7h8"
2. 前端发送请求: { type: "CREATE_ORDER", requestId: "req_a1b2c3d4e5f6g7h8", ... }
3. API写入数据库: request_id = "req_a1b2c3d4e5f6g7h8", payload = {...}
4. 币安API调用: request_id 作为 clientOrderId 的一部分
5. 结果推送: 通知携带 request_id，前端匹配请求和响应
```

### 4.3 payload 参数格式

> **注意**: payload 不再包含 requestId 字段，从顶层 request_id 获取。

| 字段 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 交易对符号 |
| `side` | string | 买卖方向 (BUY/SELL) |
| `orderType` | string | 订单类型 (LIMIT/MARKET) |
| `quantity` | number | 数量 |
| `price` | number | 价格（限价单必需） |
| `timeInForce` | string | 有效期 (GTC/IOC/FOK) |
| `clientOrderId` | string | 客户端订单ID（可选） |
| `marketType` | string | 市场类型 (SPOT/FUTURES) |

#### order.create 参数

```json
{
    "symbol": "BTCUSDT",
    "side": "BUY",
    "orderType": "LIMIT",
    "quantity": 0.002,
    "price": 50000.0,
    "timeInForce": "GTC",
    "positionSide": "BOTH",
    "reduceOnly": false,
    "clientOrderId": "my_order_001"
}
```
> 顶层字段: request_id = "req_a1b2c3d4e5f6g7h8"

#### order.cancel 参数

```json
{
    "symbol": "BTCUSDT",
    "orderId": 22542179,
    "clientOrderId": "testOrder"
}
```
> 顶层字段: request_id = "req_i9j0k1l2m3n4o5p6"

#### order.query 参数

```json
{
    "symbol": "BTCUSDT",
    "orderId": 22542179,
    "clientOrderId": "testOrder"
}
```
> 顶层字段: request_id = "req_q7r8s9t0u1v2w3x4"

### 4.3 status 状态流转

```
pending → processing → completed (成功)
         → failed     (失败)

前端显示：
- pending:    等待处理
- processing: 处理中（已发送到交易所）
- completed:  成功（result 包含订单信息）
- failed:     失败（result 包含错误信息）
```

## 5. 数据流设计

### 5.1 订单创建流程

```
1. 前端 → API 写入 order_tasks (type=order.create, status=pending)
2. INSERT 触发 notify_order_task_new()
3. binance-service 监听并处理:
   - 读取 order_tasks 获取下单参数
   - 调用币安 API 下单
   - 成功: UPDATE result=API响应, binance_order_id=xxx, status=completed
   - 失败: UPDATE result=错误信息, status=failed
4. 触发 order_task_completed / order_task_failed 通知
5. API-service 推送结果给前端
```

### 5.2 订单取消流程

```
1. 前端 → API 写入 order_tasks (type=order.cancel, status=pending)
2. INSERT 触发 notify_order_task_new()
3. binance-service 监听并处理:
   - 读取 order_tasks 获取取消参数
   - 调用币安 API 撤单
   - 成功/失败处理同上
```

### 5.3 订单状态查询流程

```
方式A: WebSocket订阅 (推荐)
  1. 前端连接 WebSocket
  2. 订阅订单更新频道
  3. 币安 WS 推送 ORDER_TRADE_UPDATE
  4. 前端实时更新订单状态

方式B: 任务查询 (兜底)
  1. 前端 → API 写入 order_tasks (type=order.query)
  2. binance-service 调用 API 查询订单状态
  3. 返回当前状态给前端
```

### 5.4 通知频道

| 频道 | 触发条件 | 发送者 | 接收者 |
|------|---------|--------|--------|
| `order_task_new` | INSERT order_tasks | 数据库 | binance-service |
| `order_task_completed` | UPDATE status=completed | 数据库 | api-service |
| `order_task_failed` | UPDATE status=failed | 数据库 | api-service |

## 6. 订单状态获取架构

### 6.1 权威数据源

```
┌─────────────────────────────────────────────────────────────────┐
│ 订单状态权威架构                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐      WebSocket       ┌──────────────┐       │
│   │   币安交易所  │ ──────────────────→  │  binance-svc │       │
│   └──────────────┘    ORDER_TRADE_UPDATE └──────┬───────┘       │
│                                                    │              │
│                                                    ▼              │
│   ┌──────────────┐      推送更新           ┌──────────────┐       │
│   │    前端      │ ←────────────────────── │ api-service  │       │
│   └──────────────┘                         └──────────────┘       │
│                                                                 │
│   核心原则: 始终以币安返回的状态为准                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 兜底机制

如果 WebSocket 断开或未连接，前端可以：

1. **主动查询**：写入 `order.query` 任务，获取最新状态
2. **定时轮询**：定期查询活跃订单状态（可选优化）

## 7. 与旧设计对比

| 特性 | 旧设计 (trading_orders) | 新设计 (order_tasks) |
|------|------------------------|---------------------|
| 存储内容 | 订单状态 + 订单数据 | 订单操作任务 |
| 状态维护 | 本地维护，可不一致 | 以交易所为准 |
| 状态获取 | 查询本地表 | WebSocket 推送 |
| 错误处理 | 状态可能卡在 NEW | 明确标记 failed |
| 数据一致性 | 难以保证 | 权威数据源 |
| 表结构 | 专用设计 | 复用 tasks 表 |
| 数据保留 | 未明确 | 永久保留 |

## 9. 使用示例

### 9.1 创建订单任务

```python
# 前端或 API 创建订单任务
# request_id 格式: req_a1b2c3d4e5f6g7h8 (UUID前16位)

# 写入数据库（request_id 提升到顶层字段）
await pool.execute("""
    INSERT INTO order_tasks (
        type, request_id, payload, status
    ) VALUES ($1, $2, $3, $4)
""",
    "order.create",
    "req_a1b2c3d4e5f6g7h8",  # 顶层字段 request_id
    {
        "clientOrderId": "my_order_001",
        "marketType": "FUTURES",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "orderType": "LIMIT",
        "quantity": 0.002,
        "price": 50000.0,
        "timeInForce": "GTC"
    },
    "pending"
)
```

### 9.2 查询订单任务结果

```python
# 通过 request_id 顶层字段查询（可建索引，查询高效）
request_id = "req_a1b2c3d4e5f6g7h8"

row = await pool.fetchrow("""
    SELECT * FROM order_tasks
    WHERE request_id = $1
    ORDER BY created_at DESC
    LIMIT 1
""", request_id)

if row["status"] == "completed":
    order_data = row["result"]
elif row["status"] == "failed":
    error_info = row["result"]
```

### 9.3 查询订单状态（向交易所查询）

```python
# 创建查询任务
# request_id 格式: req_a1b2c3d4e5f6g7h8

await pool.execute("""
    INSERT INTO order_tasks (
        type, request_id, payload, status
    ) VALUES ($1, $2, $3, $4)
""",
    "order.query",
    "req_i9j0k1l2m3n4o5p6",  # 顶层字段 request_id
    {
        "marketType": "FUTURES",
        "symbol": "BTCUSDT",
        "orderId": binance_order_id
    },
    "pending"
)

# 等待处理完成后查询结果
row = await pool.fetchrow("""
    SELECT * FROM order_tasks
    WHERE request_id = $1 AND type = 'order.query'
    ORDER BY created_at DESC
    LIMIT 1
""", request_id)

# result 中包含交易所返回的当前订单状态
current_status = row["result"]["status"]
```

## 9. 相关文档

- [QUANT_TRADING_SYSTEM_ARCHITECTURE.md](./QUANT_TRADING_SYSTEM_ARCHITECTURE.md) - 完整实施文档
- [03-binance-service.md](./03-binance-service.md) - 币安服务交易功能设计
- [01-task-subscription.md](./01-task-subscription.md) - 任务与订阅管理
- [02-dataflow.md](./02-dataflow.md) - 数据流设计

---

**版本**: v2.2
**更新**: 2026-03-04 - request_id 从 payload 提升到顶层字段；tasks 表也添加 request_id 字段保持统一
