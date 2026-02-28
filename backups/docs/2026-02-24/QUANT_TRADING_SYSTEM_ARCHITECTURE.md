# 量化交易系统架构设计

> **本文档是详细实施指南**，包含完整的数据库表结构、触发器、流程图等。
> 核心理念请参考 [DATABASE_COORDINATED_ARCHITECTURE.md](./DATABASE_COORDINATED_ARCHITECTURE.md)

## 文档导航

### 快速索引

| 主题 | 详细文档 |
|------|----------|
| 任务与订阅管理 | [01-task-subscription.md](./01-task-subscription.md) |
| 数据流设计 | [02-dataflow.md](./02-dataflow.md) |
| 币安服务 | [03-binance-service.md](./03-binance-service.md) |
| 信号服务 | [05-signal-service.md](./05-signal-service.md) |
| 告警服务 | [06-alert-service.md](./06-alert-service.md) |
| TradingView API | [tradingview-api.md](./TradingView-完整API规范设计文档.md) |
| K线表优化 | [../database/kline-optimization.md](../database/kline-optimization.md) |

## 核心概念

### 两种数据交互类型

| 类型 | 特点 | 处理方式 |
|------|------|----------|
| **一次性请求** | 前端发起一次请求，获取一次响应 | 通过 tasks 表 + 任务队列 |
| **持续订阅** | 前端订阅后持续接收更新 | 通过 realtime_data 表 + 触发器 |

### 数据模型

| 表 | 用途 |
|---|------|
| `tasks` | 一次性请求任务 |
| `klines_history` | K线历史数据 |
| `realtime_data` | 实时数据状态 |
| `exchange_info` | 交易对信息 |
| `strategy_signals` | 策略信号 |
| `alert_configs` | 告警配置 |

### 事件流

```
写入 → 触发 → 通知 → 订阅
```

**K线事件链**: 采集 → 写入 → kline.new → 信号计算
**信号事件链**: 信号写入 → signal.new → 交易决策
**交易事件链**: 交易执行 → trade.completed → 账户更新

## 目录结构

```
docs/backend/
├── design/
│   ├── DATABASE_COORDINATED_ARCHITECTURE.md  # 核心理念
│   ├── QUANT_TRADING_SYSTEM_ARCHITECTURE.md # 本文档（索引）
│   ├── 01-task-subscription.md               # 任务与订阅
│   ├── 02-dataflow.md                        # 数据流
│   ├── 03-binance-service.md                 # 币安服务
│   ├── 05-signal-service.md                  # 信号服务
│   ├── 06-alert-service.md                   # 告警服务
│   └── tradingview-api.md                    # TV API
├── database/
│   └── kline-optimization.md                 # K线优化
└── events/
    └── (待创建)
```

## 相关资源

- **数据库初始化**: `docker/init-scripts/01-database-init.sql`
- **API服务**: `services/api-service/`
- **币安服务**: `services/binance-service/`
- **信号服务**: `services/signal-service/`

## 前端设计

前端采用 Electron + Vue 3 + Vite 架构，详见 `frontend/trading-panel/CLAUDE.md`。

### 前端模块

| 模块 | 组件 | 说明 |
|------|------|------|
| K线图表 | `TradingViewChart/` | TradingView 金融图表 |
| 告警管理 | `AlertDashboard.vue` | 告警配置和信号展示 |
| 账户信息 | `AccountDashboard.vue` | 期货/现货账户信息 |

### 前端 Store

| Store | 用途 |
|-------|------|
| `tab-store.ts` | 标签页管理 |
| `alert-store.ts` | 告警状态管理 |
| `account-store.ts` | 账户信息状态管理 |

---

**版本**：v3.1
**更新**：2026-02-24 - 添加账户信息功能
**上一版本**：v3.0 (2026-02-21)
