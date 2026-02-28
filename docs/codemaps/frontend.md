# Frontend Codemap

> Last updated: 2026-02-22T12:00:00Z
> Overview of frontend application structure and type definitions.

## Application Overview

The frontend is a Vue 3 + TypeScript application using Vite as the build tool. It provides a trading panel interface with real-time chart visualization, signal monitoring, and alert configuration.

## Directory Structure

```
frontend/trading-panel/
├── src/
│   ├── main.ts                 # Application entry point
│   ├── components/
│   │   ├── HelloWorld.vue     # Welcome component
│   │   ├── TradingViewChart/
│   │   │   ├── index.vue      # TradingView chart wrapper
│   │   │   └── library/       # Cached TradingView library
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
│   │       └── RealtimeAlerts.vue     # Real-time alerts
│   ├── stores/                # Pinia stores
│   │   ├── tab-store.ts       # Tab navigation state
│   │   ├── strategy-store.ts  # Strategy state management
│   │   └── alert-store.ts    # Alert state management
│   ├── types/                 # TypeScript type definitions
│   │   ├── tradingview-data-models.ts
│   │   └── alert-types.ts
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
│   ├── SignalList / RealtimeSignals
│   └── AlertConfigForm / AlertConfigList / RealtimeAlerts
└── AppFooter
```

## State Management

### Tab Store (`tab-store.ts`)

Manages the active tab/panel in the application.

```typescript
interface TabState {
  activeTab: 'chart' | 'signals' | 'alerts';
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

## Key Features

| Feature | Component | Description |
|---------|-----------|-------------|
| Chart Display | `TradingViewChart/index.vue` | TradingView lightweight charts integration |
| Signal List | `SignalList.vue` | Display historical signals |
| Real-time Signals | `RealtimeSignals.vue` | WebSocket-powered live signals |
| Alert Config | `AlertConfigForm.vue` | Create/edit alert configurations |
| Alert List | `AlertConfigList.vue` | Manage existing alerts |
| Real-time Alerts | `RealtimeAlerts.vue` | Live alert notifications |

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

## File Statistics

| Category | Count |
|----------|-------|
| Vue Components | 10 |
| TypeScript Stores | 3 |
| Type Definition Files | 2 |
| Theme Files | 1 |
