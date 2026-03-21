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

    -- 任务参数（JSON格式，蛇形命名与币安一致）
    -- 注意：不再包含 requestId，从顶层字段获取
    -- order.create: {symbol, side, type, quantity, new_client_order_id, price, time_in_force, position_side, ...}
    -- order.cancel: {symbol, orderId, new_client_order_id}
    -- order.query:  {symbol, orderId, new_client_order_id}
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
| `order.modify` | 修改订单 | 前端请求 |
| `order.cancel` | 取消订单 | 前端请求 |
| `order.query` | 查询订单状态 | 前端请求 / 定时任务 |

### 4.2 request_id 请求ID（重要）

> **设计决策**: `request_id` 从 payload 提升到顶层字段，原因：
> 1. **贯穿整个数据流**: 前端生成 → API写入 → 结果推送
> 2. **可建索引优化**: 顶层字段可建索引，查询效率高
> 3. **语义更清晰**: 顶层字段表示"WS请求身份"，用于关联请求与响应
> 4. **与 tasks 表统一**: 保持两张表结构一致

| 字段 | 类型 | 说明 |
|------|------|------|
| `request_id` | VARCHAR(50) | WS请求追踪ID（前端生成，UUID v4 hex 格式，32字符），用于关联请求与响应 |

> **requestId vs newClientOrderId 区分**：
> - `requestId`: WS请求追踪ID，用于前端判断请求是否成功送达
> - `newClientOrderId`: 订单标识ID，用于在前端和交易所层面追踪订单状态
> - 两者独立生成，各自有不同的用途

**数据流示例**:
```
1. 前端生成 request_id: "550e8400e29b41d4a716446655440000"
2. 前端生成 new_client_order_id: "660e8400e29b41d4a716446655440001"
3. 前端发送请求: { type: "CREATE_ORDER", requestId: "550e8400...", data: {newClientOrderId: "660e8400..."} }
4. API写入数据库: request_id = "550e8400...", payload包含 new_client_order_id = "660e8400..."
5. 币安API调用: 使用 new_client_order_id 作为 clientOrderId
6. 结果推送: 通知携带 request_id，前端匹配请求和响应
```

### 4.3 payload 参数格式（蛇形命名）

> **重要**：
> - 完全采用币安蛇形命名，与币安API格式完全一致
> - 通过交易对符号前缀区分期货/现货
> - **`new_client_order_id` 为必填字段**（与币安官方不同，本项目强制要求）
> - 格式：UUID v4 hex 格式（32字符），前端生成

#### 期货 vs 现货区分

通过交易对符号前缀区分：

| 前缀 | 市场 | 示例 |
|------|------|------|
| `BINANCE:` | 现货 | `BINANCE:BTCUSDT` |
| `BINANCE:` + `.PERP` 后缀 | U本位永续合约 | `BINANCE:BTCUSDT.PERP` |

后端根据 symbol 前缀自动识别市场类型，payload 中不再包含 `marketType` 字段。

---

#### 期货订单参数 (Futures)

**必填参数**:
| 字段 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 交易对符号（如 BTCUSDT） |
| `side` | string | 买卖方向 (BUY/SELL) |
| `type` | string | 订单类型：LIMIT, MARKET, STOP, STOP_MARKET, TAKE_PROFIT, TAKE_PROFIT_MARKET, TRAILING_STOP_MARKET |
| `quantity` | float | 数量 |
| `new_client_order_id` | string | 客户端订单ID（**必填**，UUID格式，32字符） |

**可选参数** (严格遵循官方 API):
| 字段 | 类型 | 说明 |
|------|------|------|
| `position_side` | string | 持仓方向：BOTH/LONG/SHORT（**对冲模式必填**，单向模式可选） |
| `price` | float | 限价价格（LIMIT 订单必填） |
| `time_in_force` | string | 有效期：GTC/IOC/FOK/GTD |
| `reduce_only` | bool | 是否只减仓 |
| `stop_price` | float | 止损/止盈价格 |
| `callback_rate` | float | 回调比例（0.1-10，仅追踪止损） |
| `new_order_resp_type` | string | 响应格式：ACK/RESULT（默认ACK） |
| `price_match` | string | 价格匹配模式：OPPONENT/QUEUE 等 |
| `self_trade_prevention_mode` | string | 自成交防止模式 |
| `good_till_date` | int | GTD 订单过期时间 |

**期货不支持以下参数**（已移除）:
- ❌ `closePosition`
- ❌ `activationPrice`
- ❌ `workingType`
- ❌ `priceProtect`

**期货下单示例**:
```json
{
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "quantity": 0.002,
    "price": 50000.0,
    "time_in_force": "GTC",
    "position_side": "BOTH",
    "reduce_only": false
}
```

---

#### 现货订单参数 (Spot)

**必填参数**:
| 字段 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 交易对符号（如 BTCUSDT） |
| `side` | string | 买卖方向 (BUY/SELL) |
| `type` | string | 订单类型：LIMIT, MARKET, LIMIT_MAKER, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT, TRAILING_STOP_MARKET |
| `quantity` | float | 数量（市价单可使用 quoteOrderQty 替代） |
| `new_client_order_id` | string | 客户端订单ID（**必填**，UUID格式，32字符） |

**可选参数** (严格遵循官方 API):
| 字段 | 类型 | 说明 |
|------|------|------|
| `price` | float | 限价价格（LIMIT/LIMIT_MAKER 订单必填） |
| `time_in_force` | string | 有效期：GTC/IOC/FOK |
| `quote_order_qty` | float | 报价数量（市价买单时指定支付金额） |
| `stop_price` | float | 止损价格（止损单必需） |
| `iceberg_qty` | float | 冰山订单数量 |
| `trailing_delta` | int | 追踪止损 delta |
| `strategy_id` | int | 策略ID |
| `strategy_type` | int | 策略类型（值不能小于 1000000） |
| `new_order_resp_type` | string | 响应格式：ACK/RESULT/FULL（默认FULL） |
| `self_trade_prevention_mode` | string | 自成交防止模式 |

**现货不支持以下参数**:
- ❌ `position_side`
- ❌ `reduce_only`

**现货下单示例**:
```json
{
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "quantity": 0.002,
    "new_client_order_id": "660e8400e29b41d4a716446655440001",
    "price": 50000.0,
    "time_in_force": "GTC"
}
```

---

#### order.create 参数（旧版本兼容）

> **注意**: 以下为后端 payload 存储格式，前端无需关注

#### order.cancel 参数（取消订单）

**命名规则**：前端发送 camelCase，后端自动转换为 snake_case 存储

```json
{
    "symbol": "BTCUSDT",
    "orderId": 22542179,
    "origClientOrderId": "660e8400e29b41d4a716446655440001",
    "newClientOrderId": "770e8400e29b41d4a716446655440002",
    "cancelRestrictions": "ONLY_NEW"
}
```
> 顶层字段: request_id = "660e8400e29b41d4a716446655440001"
> **必填**：`symbol`，以及 `orderId` 或 `origClientOrderId`（二选一）
>
> **ID 优先级**：`orderId`（币安生成的订单ID）> `origClientOrderId`（客户端自定义ID）
> - `orderId` 存在时优先使用
> - `orderId` 不存在时使用 `origClientOrderId`

##### 现货特有可选参数（前端 camelCase，后端自动转换）

| 前端字段 (camelCase) | 后端字段 (snake_case) | 类型 | 说明 |
|---------------------|----------------------|------|------|
| `newClientOrderId` | `new_client_order_id` | string | 用于唯一标识此次取消操作，自动生成 |
| `cancelRestrictions` | `cancel_restrictions` | string | 取消限制条件：`ONLY_NEW`、`ONLY_PARTIALLY_FILLED` |

> **注意**：期货 (fapi) 不支持 `newClientOrderId` 和 `cancelRestrictions` 参数，仅现货 (api) 支持。

#### order.query 参数（查询订单）

**命名规则**：前端发送 camelCase，后端自动转换为 snake_case 存储

```json
{
    "symbol": "BTCUSDT",
    "orderId": 22542179,
    "origClientOrderId": "660e8400e29b41d4a716446655440001"
}
```
> 顶层字段: request_id = "770e8400e29b41d4a716446655440002"
> **必填**：`symbol`，以及 `orderId` 或 `origClientOrderId`（二选一）
>
> **ID 优先级**：`orderId`（币安生成的订单ID）> `origClientOrderId`（客户端自定义ID）

> **说明**：查询订单 API 现货和期货参数完全一致，无额外可选参数。

#### order.modify 参数（修改订单）

> **重要**：期货和现货使用不同的 API，参数差异较大：
> - 期货 (WS): `order.modify` - 可修改价格和数量，**仅支持 LIMIT 订单**
> - 现货 (WS): `order.amend.keepPriority` - 只能减少数量

##### 期货修改订单参数 (Futures)

**WS Method**: `order.modify`

**命名规则**：前端发送 camelCase，后端自动转换为 snake_case 存储

```json
{
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": 0.003,
    "price": 51000.0,
    "origClientOrderId": "660e8400e29b41d4a716446655440001",
    "newClientOrderId": "770e8400e29b41d4a716446655440002",
    "positionSide": "BOTH",
    "timestamp": 1703426755754
}
```
> 顶层字段: request_id = "550e8400e29b41d4a716446655440000"
> **必填**：`symbol`, `side`, `quantity`, `price`, `timestamp`，以及 `orderId` 或 `origClientOrderId`（二选一）
>
> **ID 优先级**：`orderId`（币安生成的订单ID）> `origClientOrderId`（客户端自定义ID）

| 字段 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 交易对符号 |
| `side` | string | 订单方向：BUY 或 SELL |
| `quantity` | float | 新订单数量 |
| `price` | float | 新订单价格 |
| `timestamp` | long | **必填** 时间戳（毫秒） |
| `orderId` | int | 订单ID（与 origClientOrderId 二选一，**优先使用**） |
| `origClientOrderId` | string | 客户端订单ID（与 orderId 二选一） |
| `newClientOrderId` | string | 新客户端订单ID（可选，用于标识此次修改） |
| `positionSide` | string | 持仓方向：BOTH/LONG/SHORT（可选） |
| `priceMatch` | string | 价格匹配模式（可选，仅适用于 LIMIT/STOP/TAKE_PROFIT 订单） |
| `recvWindow` | long | 接收窗口时间（可选） |

> **限制说明**：
> - 仅支持 LIMIT 订单修改
> - priceMatch 与 price 不能同时使用
> - 新数量或价格不满足过滤器规则时修改会被拒绝
> - 部分成交时新数量 <= 已成交数量会导致订单被取消
> - GTX 订单新价格导致立即成交会取消订单
> - 单个订单最多修改 10000 次

##### 现货修改订单参数 (Spot)

**WS Method**: `order.amend.keepPriority`

**命名规则**：前端发送 camelCase，后端自动转换为 snake_case 存储

```json
{
    "symbol": "BTCUSDT",
    "origClientOrderId": "660e8400e29b41d4a716446655440001",
    "newClientOrderId": "770e8400e29b41d4a716446655440002",
    "newQty": 0.001,
    "timestamp": 1741922620419
}
```
> 顶层字段: request_id = "550e8400e29b41d4a716446655440000"
> **必填**：`symbol`, `newQty`, `timestamp`，以及 `orderId` 或 `origClientOrderId`（二选一）
>
> **ID 优先级**：`orderId`（币安生成的订单ID）> `origClientOrderId`（客户端自定义ID）

| 字段 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 交易对符号 |
| `timestamp` | long | **必填** 时间戳（毫秒） |
| `orderId` | int | 订单ID（与 origClientOrderId 二选一，**优先使用**） |
| `origClientOrderId` | string | 客户端订单ID（与 orderId 二选一） |
| `newClientOrderId` | string | 新客户端订单ID（可选） |
| `newQty` | float | 新订单数量，**必须大于0且小于原订单数量** |
| `recvWindow` | long | 接收窗口时间（可选，最大 60000） |

> **限制说明**：
> - 只能**减少**数量，不能增加数量或修改价格
> - 响应中的订单数据在 `amendedOrder` 字段内
> - 不会增加 EXCHANGE_MAX_ORDERS 和 MAX_NUM_ORDERS 过滤器的计数

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

### 5.3 订单修改流程

```
1. 前端 → API 写入 order_tasks (type=order.modify, status=pending)
2. INSERT 触发 notify_order_task_new()
3. binance-service 监听并处理:
   - 读取 order_tasks 获取修改参数
   - 期货: 调用币安 fapi/order.modify API
   - 现货: 调用币安 api/order.amend API
   - 成功: UPDATE result=API响应, status=completed
   - 失败: UPDATE result=错误信息, status=failed
4. 触发 order_task_completed / order_task_failed 通知
5. API-service 推送结果给前端
```

> **期货 vs 现货差异**：
> - 期货 (`order.modify`)：可修改价格和数量，修改后订单重新排队
> - 现货 (`order.amend.keepPriority`)：只能减少数量，保持订单簿优先级

**响应格式差异**（详见 08-api-models.md）：
> - 期货：使用 `FuturesModifyOrderResponse` 模型，直接返回订单对象
> - 现货：使用 `SpotAmendOrderResponse` 模型，返回 `{transactTime, executionId, amendedOrder}`
>
> **实现注意**：binance-service 处理现货响应时需要提取 `amendedOrder` 作为最终结果。

### 5.4 订单状态查询流程

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
# request_id 格式: 550e8400e29b41d4a716446655440000 (UUID前16位)

# 写入数据库（request_id 提升到顶层字段）
await pool.execute("""
    INSERT INTO order_tasks (
        type, request_id, payload, status
    ) VALUES ($1, $2, $3, $4)
""",
    "order.create",
    "550e8400e29b41d4a716446655440000",  # 顶层字段 request_id
    {
        "new_client_order_id": "660e8400e29b41d4a716446655440001",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "quantity": 0.002,
        "price": 50000.0,
        "time_in_force": "GTC"
    },
    "pending"
)
```

### 9.2 查询订单任务结果

```python
# 通过 request_id 顶层字段查询（可建索引，查询高效）
request_id = "550e8400e29b41d4a716446655440000"

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
# request_id 格式: 550e8400e29b41d4a716446655440000

await pool.execute("""
    INSERT INTO order_tasks (
        type, request_id, payload, status
    ) VALUES ($1, $2, $3, $4)
""",
    "order.query",
    "660e8400e29b41d4a716446655440001",  # 顶层字段 request_id
    {
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
- [09-binance-models.md](./09-binance-models.md) - 币安数据模型设计文档
- [01-task-subscription.md](./01-task-subscription.md) - 任务与订阅管理
- [02-dataflow.md](./02-dataflow.md) - 数据流设计

---

## 10. 币安过滤器限制（重要）

> **必读**: 下单参数必须满足币安交易所的过滤器规则，否则订单会被拒绝。

### 10.1 LOT_SIZE 过滤器（数量限制）

**官方文档**: https://developers.binance.com/docs/binance-spot-api-docs/filters

```json
{
  "filterType": "LOT_SIZE",
  "minQty": "0.00001000",
  "maxQty": "9000.00000000",
  "stepSize": "0.00001000"
}
```

**数量必须满足以下条件**：
| 条件 | 说明 |
|------|------|
| `quantity >= minQty` | 数量不能小于最小值 |
| `quantity <= maxQty` | 数量不能大于最大值 |
| `quantity % stepSize == 0` | **数量必须是 stepSize 的整数倍** |

**示例**（BTCUSDT，stepSize=0.00001）：
```
✓ 有效: 0.04397 BTC (4370 × 0.00001)
✓ 有效: 0.04398 BTC (4398 × 0.00001)
✗ 无效: 0.04397598 BTC (4397.598 × 0.00001，余数 0.000008)
✗ 无效: 0.0439 BTC (4390 × 0.00001，但可能被用户界面圆整)
```

**前端处理要求**：
```typescript
// 将数量舍入到 stepSize 的整数倍
function roundToStepSize(quantity: number, stepSize: number): number {
  return Math.floor(quantity / stepSize) * stepSize
}

// 示例
const stepSize = 0.00001  // BTCUSDT
const quantity = 0.04397598
const rounded = roundToStepSize(quantity, stepSize)  // 0.04397
```

### 10.2 PRICE_FILTER（价格限制）

**官方文档**: https://developers.binance.com/docs/binance-spot-api-docs/filters

```json
{
  "filterType": "PRICE_FILTER",
  "minPrice": "0.01000000",
  "maxPrice": "1000000.00000000",
  "tickSize": "0.01000000"
}
```

**价格必须满足以下条件**：
| 条件 | 说明 |
|------|------|
| `price >= minPrice` | 价格不能小于最小值 |
| `price <= maxPrice` | 价格不能大于最大值 |
| `price % tickSize == 0` | **价格必须是 tickSize 的整数倍** |

**示例**（BTCUSDT，tickSize=0.01）：
```
✓ 有效: 70000.00 USDT
✓ 有效: 70000.01 USDT
✗ 无效: 70000.001 USDT (不是 0.01 的整数倍)
```

### 10.3 MIN_NOTIONAL（最小名义价值）

```json
{
  "filterType": "NOTIONAL",
  "minNotional": "5.00000000",
  "applyMinToMarket": true
}
```

**名义价值 = price × quantity，必须满足**：
```
price × quantity >= minNotional
```

### 10.4 前端校验实现建议

**强烈建议前端在发送订单前进行校验**：

```typescript
interface ExchangeFilters {
  lotSize: {
    minQty: number
    maxQty: number
    stepSize: number
  }
  priceFilter: {
    minPrice: number
    maxPrice: number
    tickSize: number
  }
  minNotional: number
}

function validateOrderParams(
  quantity: number,
  price: number,
  filters: ExchangeFilters
): { valid: boolean; error?: string } {
  // 检查数量
  if (quantity < filters.lotSize.minQty) {
    return { valid: false, error: `数量低于最小值 ${filters.lotSize.minQty}` }
  }
  if (quantity > filters.lotSize.maxQty) {
    return { valid: false, error: `数量超过最大值 ${filters.lotSize.maxQty}` }
  }
  if (quantity % filters.lotSize.stepSize !== 0) {
    return { valid: false, error: `数量必须是 ${filters.lotSize.stepSize} 的整数倍` }
  }

  // 检查价格
  if (price < filters.priceFilter.minPrice) {
    return { valid: false, error: `价格低于最小值 ${filters.priceFilter.minPrice}` }
  }
  if (price > filters.priceFilter.maxPrice) {
    return { valid: false, error: `价格超过最大值 ${filters.priceFilter.maxPrice}` }
  }
  if (price % filters.priceFilter.tickSize !== 0) {
    return { valid: false, error: `价格必须是 ${filters.priceFilter.tickSize} 的整数倍` }
  }

  // 检查最小名义价值
  const notional = price * quantity
  if (notional < filters.minNotional) {
    return { valid: false, error: `订单名义价值 ${notional} 低于最小值 ${filters.minNotional}` }
  }

  return { valid: true }
}
```

### 10.5 常见错误代码

| 错误代码 | 错误信息 | 原因 |
|---------|---------|------|
| -1013 | Filter failure: LOT_SIZE | 数量不满足 stepSize 要求 |
| -1013 | Filter failure: MIN_NOTIONAL | 名义价值低于最低要求 |
| -1013 | Filter failure: PRICE_FILTER | 价格不满足 tickSize 要求 |
| -1013 | Filter failure: MAX_NOTIONAL | 名义价值超过最高限制 |

---

**版本**: v2.6
**更新**: 2026-03-19 - 添加币安过滤器限制说明（LOT_SIZE, PRICE_FILTER, MIN_NOTIONAL）

**版本**: v2.5
**更新**: 2026-03-06 - 补充现货特有可选参数：取消订单支持newClientOrderId和cancelRestrictions

**版本**: v2.4
**更新**: 2026-03-06 - 采用币安蛇形命名；newClientOrderId改为必填；去掉marketType字段，通过symbol前缀区分期货/现货；requestId与newClientOrderId区分；取消/查询使用origClientOrderId
