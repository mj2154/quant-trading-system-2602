# Frontend Codemap

> Last updated: 2026-03-01T04:42:00Z
> Overview of frontend application structure and type definitions.

## Application Overview

The frontend is a Vue 3 + TypeScript application using Vite as the build tool. It provides a trading panel interface with real-time chart visualization, signal monitoring, alert configuration, and account management.

## Directory Structure

```
frontend/trading-panel/
├── src/
│   ├── main.ts                 # Application entry point
│   ├── App.vue                 # Root component
│   ├── style.css               # Global styles
│   ├── components/
│   │   ├── HelloWorld.vue     # Welcome component
│   │   ├── GlobalAlertHandler.vue  # Global alert handling
│   │   ├── TradingViewChart/
│   │   │   ├── index.vue      # TradingView chart wrapper
│   │   │   └── library/        # Cached TradingView library
│   │   ├── layout/
│   │   │   ├── AppHeader.vue  # Application header
│   │   │   ├── AppContent.vue # Main content area
│   │   │   └── AppFooter.vue  # Application footer
│   │   ├── signal/
│   │   │   ├── SignalList.vue         # Signal list display
│   │   │   └── RealtimeSignals.vue    # Real-time signals
│   │   └── alert/
│   │       ├── AlertConfigForm.vue    # Alert configuration form
│   │       ├── AlertConfigList.vue    # Alert list display
│   │       └── RealtimeAlerts.vue    # Real-time alerts
│   │   └── trading/
│   │       ├── OrderForm.vue        # Order creation form
│   │       ├── OrderList.vue         # Order history list
│   │       ├── OrderDetail.vue       # Order detail view
│   │       └── OrderStatus.vue       # Order status badge
│   ├── views/
│   │   ├── ModuleA.vue
│   │   ├── ModuleB.vue
│   │   ├── ModuleC.vue
│   │   ├── AlertDashboard.vue
│   │   ├── AlertTest.vue
│   │   ├── AccountDashboard.vue
│   │   └── TradingDashboard.vue    # Trading panel
│   ├── stores/                # Pinia stores
│   │   ├── tab-store.ts       # Tab navigation state
│   │   ├── strategy-store.ts  # Strategy state management
│   │   ├── alert-store.ts     # Alert state management
│   │   ├── account-store.ts    # Account balance state
│   │   └── trading-store.ts    # Trading order state
│   ├── types/                 # TypeScript type definitions
│   │   ├── tradingview-data-models.ts
│   │   ├── alert-types.ts
│   │   ├── account-types.ts
│   │   └── trading-types.ts    # Trading order types
│   ├── composables/
│   │   └── useAlertSettings.ts
│   ├── theme/
│   │   └── alert-theme.ts    # Alert theming
│   └── vite-env.d.ts         # Vite type definitions
├── package.json
└── vite.config.ts
```

## Component Hierarchy

```
App
├── AppHeader
├── AppContent
│   ├── HelloWorld
│   ├── TradingViewChart
│   ├── ModuleA / ModuleB / ModuleC
│   ├── SignalList / RealtimeSignals
│   ├── AlertDashboard / AlertTest
│   ├── AccountDashboard
│   └── TradingDashboard
│       ├── OrderForm
│       ├── OrderList
│       └── OrderDetail
├── AppFooter
└── GlobalAlertHandler
```

## State Management

### Tab Store (`tab-store.ts`)

Manages the active tab/panel in the application.

```typescript
interface TabState {
  activeTab: 'chart' | 'signals' | 'alerts' | 'account';
  // ...
}
```

### Strategy Store (`strategy-store.ts`)

Manages strategy configurations and signals.

```typescript
interface StrategyState {
  strategies: StrategyConfig[];
  signals: StrategySignal[];
  // ...
}
```

### Alert Store (`alert-store.ts`)

Manages alert configurations and notifications.

```typescript
interface AlertState {
  alerts: AlertConfig[];
  notifications: Alert[];
  // ...
}
```

### Account Store (`account-store.ts`)

Manages account balances and positions.

```typescript
interface AccountState {
  balances: Balance[];
  positions: Position[];
  lastUpdate: Date;
}
```

## Type Definitions

### TradingView Data Models (`tradingview-data-models.ts`)

Type definitions for TradingView chart data integration.

### Alert Types (`alert-types.ts`)

```typescript
interface AlertConfig {
  id: string;
  name: string;
  symbol: string;
  condition: AlertCondition;
  enabled: boolean;
}

interface AlertCondition {
  type: 'price_above' | 'price_below' | 'signal';
  value?: number;
}

interface Alert {
  id: string;
  alertId: string;
  message: string;
  timestamp: Date;
}
```

### Account Types (`account-types.ts`)

```typescript
interface Balance {
  asset: string;
  free: string;
  locked: string;
}

interface Position {
  symbol: string;
  positionSide: 'LONG' | 'SHORT' | 'BOTH';
  positionAmt: string;
  entryPrice: string;
  markPrice: string;
  unrealProfit: string;
}

interface AccountInfo {
  balances: Balance[];
  totalAssetInBtc: string;
  totalAssetInUsdt: string;
}
```

### Trading Types (`trading-types.ts`)

```typescript
// 市场类型
type MarketType = 'FUTURES' | 'SPOT';

// 订单方向
type OrderSide = 'BUY' | 'SELL';

// 订单类型
type OrderType = 'LIMIT' | 'MARKET' | 'STOP' | 'STOP_LOSS' | 'STOP_LOSS_LIMIT' | 'TAKE_PROFIT' | 'TAKE_PROFIT_LIMIT' | 'LIMIT_MAKER';

// 持仓方向
type PositionSide = 'BOTH' | 'LONG' | 'SHORT';

// 时间策略
type TimeInForce = 'GTC' | 'IOC' | 'FOK' | 'GTD';

// 订单状态
type OrderStatus = 'NEW' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELED' | 'PENDING_CANCEL' | 'REJECTED' | 'EXPIRED';

// 创建订单请求
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

// 订单数据
interface Order {
  clientOrderId: string;
  binanceOrderId?: number;
  marketType: MarketType;
  symbol: string;
  side: OrderSide;
  orderType: OrderType;
  status: OrderStatus;
  data: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

// 订单列表响应
interface OrderListResponse {
  orders: Order[];
  count: number;
}

// 订单更新推送
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

## Key Features

| Feature | Component | Description |
|---------|-----------|-------------|
| Chart Display | `TradingViewChart/index.vue` | TradingView lightweight charts integration |
| Signal List | `SignalList.vue` | Display historical signals |
| Real-time Signals | `RealtimeSignals.vue` | WebSocket-powered live signals |
| Alert Config | `AlertConfigForm.vue` | Create/edit alert configurations |
| Alert List | `AlertConfigList.vue` | Manage existing alerts |
| Real-time Alerts | `RealtimeAlerts.vue` | Live alert notifications |
| Alert Dashboard | `AlertDashboard.vue` | Overview of all alerts |
| Alert Testing | `AlertTest.vue` | Test alert sounds |
| Account Overview | `AccountDashboard.vue` | View balances and positions |
| Trading Panel | `TradingPanel.vue` | Trading order management |
| Order Form | `OrderForm.vue` | Create/place trading orders |
| Order List | `OrderList.vue` | View order history |
| Order Detail | `OrderDetail.vue` | View order details |

## Trading Feature

### WebSocket 消息类型

交易功能通过 WebSocket 与 API 服务通信，消息类型定义在 `07-websocket-protocol.md`：

| 请求类型 | 响应类型 | 说明 |
|---------|---------|------|
| `CREATE_ORDER` | `ORDER_DATA` | 创建订单 |
| `GET_ORDER` | `ORDER_DATA` | 查询单个订单 |
| `LIST_ORDERS` | `ORDER_LIST_DATA` | 查询订单列表 |
| `CANCEL_ORDER` | `ORDER_DATA` | 撤销订单 |
| `GET_OPEN_ORDERS` | `ORDER_LIST_DATA` | 查询当前挂单 |

### 订单类型定义

```typescript
// 订单请求
interface CreateOrderRequest {
  marketType: 'FUTURES' | 'SPOT';
  symbol: string;
  side: 'BUY' | 'SELL';
  orderType: 'LIMIT' | 'MARKET' | 'STOP' | 'TAKE_PROFIT';
  quantity: number;
  price?: number;
  timeInForce?: 'GTC' | 'IOC' | 'FOK';
  stopPrice?: number;
  reduceOnly?: boolean;
  positionSide?: 'BOTH' | 'LONG' | 'SHORT';
}

// 订单数据
interface OrderData {
  clientOrderId: string;
  binanceOrderId?: number;
  marketType: 'FUTURES' | 'SPOT';
  symbol: string;
  side: 'BUY' | 'SELL';
  orderType: string;
  status: 'NEW' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELED' | 'REJECTED' | 'EXPIRED';
  data: Record<string, unknown>;  // 币安API完整响应
  createdAt: string;
  updatedAt: string;
}

// 订单列表
interface OrderListData {
  orders: OrderData[];
  count: number;
}

// 订单更新推送
interface OrderUpdate {
  clientOrderId: string;
  binanceOrderId?: number;
  marketType: 'FUTURES' | 'SPOT';
  symbol: string;
  side: 'BUY' | 'SELL';
  orderType: string;
  status: string;
  data: Record<string, unknown>;
  updatedAt: string;
}
```

### Trading Store (`trading-store.ts`)

管理交易订单状态：

```typescript
interface TradingState {
  orders: OrderData[];
  openOrders: OrderData[];
  currentOrder: OrderData | null;
  isLoading: boolean;
  lastUpdate: Date;
}
```

### Trading Panel 功能

| 功能 | 说明 |
|------|------|
| 市场选择 | 期货(FUTURES) / 现货(SPOT) 切换 |
| 交易对选择 | 选择交易对如 BTCUSDT |
| 订单类型 | LIMIT / MARKET / STOP / TAKE_PROFIT |
| 买入/卖出 | 选择 BUY 或 SELL |
| 价格设置 | 限价单设置价格 |
| 数量设置 | 设置下单数量 |
| 持仓方向 | 期货选择 LONG / SHORT / BOTH |
| 订单列表 | 查看历史订单和当前挂单 |
| 订单详情 | 查看订单详细信息和状态 |
| 撤销订单 | 撤销当前挂单 |
| 实时更新 | WebSocket 推送订单状态更新 |

## Technology Stack

| Category | Technology |
|----------|-----------|
| Framework | Vue 3 (Composition API) |
| Language | TypeScript |
| Build Tool | Vite |
| State Management | Pinia |
| Charts | TradingView Lightweight Charts |
| Styling | CSS (per-component) |
| Package Manager | npm |

## WebSocket Integration

The frontend connects to the API service via WebSocket for real-time updates:

- Kline updates
- Signal generation events
- Alert notifications
- Account balance updates
- Order status updates (order creation, fills, cancellation)

## File Statistics

| Category | Count |
|----------|-------|
| Vue Components | 22 |
| TypeScript Stores | 5 |
| Type Definition Files | 4 |
| Theme Files | 1 |
| Composable Functions | 1 |

## Recent Updates (Since Feb 22)

1. Added `account-store.ts` for account state management
2. Added `account-types.ts` with Balance and Position types
3. Added `AccountDashboard.vue` for viewing account info
4. Added `GlobalAlertHandler.vue` for global alert handling
5. Added `AlertTest.vue` for testing alert sounds
6. Added `AlertDashboard.vue` for alert overview
7. Added `trading-store.ts` for trading order state management
8. Added `trading-types.ts` with Order and trading types
9. Added `TradingDashboard.vue` for trading panel
10. Added trading components: OrderForm, OrderList, OrderDetail
