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
│   ├── views/
│   │   ├── ModuleA.vue
│   │   ├── ModuleB.vue
│   │   ├── ModuleC.vue
│   │   ├── AlertDashboard.vue
│   │   ├── AlertTest.vue
│   │   └── AccountDashboard.vue
│   ├── stores/                # Pinia stores
│   │   ├── tab-store.ts       # Tab navigation state
│   │   ├── strategy-store.ts  # Strategy state management
│   │   ├── alert-store.ts     # Alert state management
│   │   └── account-store.ts   # Account balance state
│   ├── types/                 # TypeScript type definitions
│   │   ├── tradingview-data-models.ts
│   │   ├── alert-types.ts
│   │   └── account-types.ts
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
│   └── AccountDashboard
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

## File Statistics

| Category | Count |
|----------|-------|
| Vue Components | 16 |
| TypeScript Stores | 4 |
| Type Definition Files | 3 |
| Theme Files | 1 |
| Composable Functions | 1 |

## Recent Updates (Since Feb 22)

1. Added `account-store.ts` for account state management
2. Added `account-types.ts` with Balance and Position types
3. Added `AccountDashboard.vue` for viewing account info
4. Added `GlobalAlertHandler.vue` for global alert handling
5. Added `AlertTest.vue` for testing alert sounds
6. Added `AlertDashboard.vue` for alert overview
