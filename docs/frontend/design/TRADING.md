# 前端交易功能设计

本文档描述量化交易系统前端的交易功能设计。

## 1. 功能概述

交易功能允许用户通过前端界面进行期货和现货的下单、撤单、查询等操作。

## 2. WebSocket 通信

交易功能通过 WebSocket 与 API 服务通信，消息协议定义见 `07-websocket-protocol.md`。

### 2.1 消息类型

| 请求类型 | 响应类型 | 说明 |
|---------|---------|------|
| `CREATE_ORDER` | `ORDER_DATA` | 创建订单 |
| `GET_ORDER` | `ORDER_DATA` | 查询单个订单 |
| `LIST_ORDERS` | `ORDER_LIST_DATA` | 查询订单列表 |
| `CANCEL_ORDER` | `ORDER_DATA` | 撤销订单 |
| `GET_OPEN_ORDERS` | `ORDER_LIST_DATA` | 查询当前挂单 |

### 2.2 订单更新推送

| 消息类型 | 说明 |
|---------|------|
| `ORDER_UPDATE` | 订单状态更新推送 |

## 3. 组件设计

### 3.1 组件结构

```
src/
├── components/
│   └── trading/
│       ├── OrderForm.vue        # 订单创建表单
│       ├── OrderList.vue       # 订单历史列表
│       ├── OrderDetail.vue     # 订单详情
│       └── OrderStatus.vue     # 订单状态徽章
├── views/
│   └── TradingDashboard.vue    # 交易面板主视图
├── stores/
│   └── trading-store.ts        # 交易状态管理
└── types/
    └── trading-types.ts       # 交易类型定义
```

### 3.2 组件说明

| 组件 | 说明 |
|------|------|
| TradingDashboard | 交易面板主视图，包含订单表单和订单列表 |
| OrderForm | 订单创建表单，支持市价/限价/止损单 |
| OrderList | 订单历史列表，支持筛选和分页 |
| OrderDetail | 订单详情弹窗，显示完整订单信息 |
| OrderStatus | 订单状态徽章，显示订单当前状态 |

## 4. 状态管理

### 4.1 Trading Store

```typescript
interface TradingState {
  orders: Order[];           // 订单列表
  openOrders: Order[];      // 当前挂单
  currentOrder: Order | null; // 当前选中的订单
  isLoading: boolean;       // 加载状态
  error: string | null;     // 错误信息
  lastUpdate: Date;         // 最后更新时间
}
```

### 4.2 Actions

- `createOrder(params)` - 创建订单
- `fetchOrder(clientOrderId)` - 获取订单
- `fetchOrders(filters)` - 获取订单列表
- `fetchOpenOrders(marketType)` - 获取挂单
- `cancelOrder(clientOrderId)` - 撤销订单

## 5. 类型定义

### 5.1 基础类型

```typescript
// 市场类型
type MarketType = 'FUTURES' | 'SPOT';

// 订单方向
type OrderSide = 'BUY' | 'SELL';

// 订单类型
type OrderType = 'LIMIT' | 'MARKET' | 'STOP' | 'STOP_LOSS' | 'STOP_LOSS_LIMIT' |
                 'TAKE_PROFIT' | 'TAKE_PROFIT_LIMIT' | 'LIMIT_MAKER';

// 持仓方向
type PositionSide = 'BOTH' | 'LONG' | 'SHORT';

// 时间策略
type TimeInForce = 'GTC' | 'IOC' | 'FOK' | 'GTD';

// 订单状态
type OrderStatus = 'NEW' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELED' |
                   'PENDING_CANCEL' | 'REJECTED' | 'EXPIRED';
```

### 5.2 请求类型

```typescript
interface CreateOrderParams {
  marketType: MarketType;
  symbol: string;
  side: OrderSide;
  orderType: OrderType;
  quantity: number;
  price?: number;
  timeInForce?: TimeInForce;
  stopPrice?: number;
  reduceOnly?: boolean;
  positionSide?: PositionSide;
}
```

### 5.3 响应类型

```typescript
interface Order {
  clientOrderId: string;
  binanceOrderId?: number;
  marketType: MarketType;
  symbol: string;
  side: OrderSide;
  orderType: OrderType;
  status: OrderStatus;
  data: Record<string, unknown>;  // 币安API完整响应
  createdAt: string;
  updatedAt: string;
}

interface OrderListResponse {
  orders: Order[];
  count: number;
}

interface OrderUpdate {
  clientOrderId: string;
  binanceOrderId?: number;
  marketType: MarketType;
  symbol: string;
  side: OrderSide;
  orderType: OrderType;
  status: OrderStatus;
  data: Record<string, unknown>;
  updatedAt: string;
}
```

## 6. 订单表单功能

### 6.1 市场选择

- 期货 (FUTURES)
- 现货 (SPOT)

### 6.2 订单类型

| 类型 | 说明 | 必需参数 |
|------|------|----------|
| LIMIT | 限价单 | price, quantity, timeInForce |
| MARKET | 市价单 | quantity |
| STOP | 止损单 | stopPrice, quantity |
| TAKE_PROFIT | 止盈单 | stopPrice, quantity |

### 6.3 持仓方向（仅期货）

- BOTH - 单向持仓
- LONG - 多头
- SHORT - 空头

### 6.4 订单参数

- 交易对选择
- 买入/卖出
- 数量
- 价格（限价单）
- 止损价格（条件单）
- 仅减仓（期货）

## 7. 订单列表功能

### 7.1 筛选条件

- 市场类型
- 交易对
- 订单状态
- 订单方向

### 7.2 显示信息

- 订单ID
- 交易对
- 方向（买/卖）
- 类型
- 数量
- 价格
- 状态
- 时间

### 7.3 操作

- 查看详情
- 撤销订单

## 8. 实时更新

### 8.1 订阅机制

订单状态通过 WebSocket 实时推送：

```typescript
// 订阅订单更新
ws.send({
  type: 'SUBSCRIBE',
  subscriptions: ['TRADING:ORDER']
});
```

### 8.2 更新处理

当收到订单更新推送时：
1. 解析订单数据
2. 更新 trading store 中的订单状态
3. 显示通知给用户

## 9. 相关文档

- [WebSocket协议](../backend/design/07-websocket-protocol.md)
- [交易订单表设计](../backend/design/04-trading-orders.md)
- [API服务交易功能](../backend/design/05-signal-service.md) (设计思路)

---

**版本**: v1.0
**更新**: 2026-03-02
