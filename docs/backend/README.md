# 后端架构文档

## 文档体系

系统架构文档采用**分层文档架构**，理念与实施分离：

### 核心理念文档

| 文档 | 说明 |
|------|------|
| `design/DATABASE_COORDINATED_ARCHITECTURE.md` | 架构哲学、设计原则、抽象模型 |
| `design/QUANT_TRADING_SYSTEM_ARCHITECTURE.md` | 实施指南、数据库设计、表结构 |

### 服务设计文档

按服务模块组织的设计文档：

| 文档 | 说明 |
|------|------|
| `design/01-task-subscription.md` | 任务订阅与调度机制 |
| `design/02-dataflow.md` | 数据流与事件链设计 |
| `design/03-binance-service.md` | 币安服务设计与实现 |
| `design/04-dataprocessor.md` | 数据处理器设计 |
| `design/04-trading-orders.md` | 交易订单处理 |
| `design/05-signal-service.md` | 信号服务设计 |
| `design/06-alert-service.md` | 告警服务设计 |
| `design/07-api-service.md` | API 服务基础 |

### 协议与模型文档

| 文档 | 说明 |
|------|------|
| `design/07-websocket-protocol.md` | WebSocket 通信协议 |
| `design/07a-websocket-messages.md` | WebSocket 消息格式 |
| `design/07b-websocket-errorcodes.md` | WebSocket 错误码定义 |
| `design/07c-websocket-changelog.md` | WebSocket 协议变更日志 |
| `design/08-api-models.md` | API 数据模型定义 |

### 数据库设计

| 文档 | 说明 |
|------|------|
| `database/Kline-Table-Event-Optimization.md` | K线表优化与事件设计 |

### 实现报告

| 文档 | 说明 |
|------|------|
| `implementation/REPORT-api-service-models-refactor.md` | API服务模型重构报告 |
| `implementation/REPORT-binance-service-models-refactor.md` | 币安服务模型重构报告 |

## 目录结构

```
docs/backend/
├── design/                        # 核心设计文档
│   ├── DATABASE_COORDINATED_ARCHITECTURE.md   # 核心理念
│   ├── QUANT_TRADING_SYSTEM_ARCHITECTURE.md   # 实施指南
│   ├── 01-task-subscription.md    # 任务订阅
│   ├── 02-dataflow.md             # 数据流
│   ├── 03-binance-service.md      # 币安服务
│   ├── 04-dataprocessor.md        # 数据处理器
│   ├── 04-trading-orders.md       # 交易订单
│   ├── 05-signal-service.md       # 信号服务
│   ├── 06-alert-service.md        # 告警服务
│   ├── 07-api-service.md          # API服务
│   ├── 07-websocket-protocol.md   # WebSocket协议
│   ├── 07a-websocket-messages.md  # WebSocket消息
│   ├── 07b-websocket-errorcodes.md # WebSocket错误码
│   ├── 07c-websocket-changelog.md # WebSocket变更日志
│   ├── 08-api-models.md           # API模型
│   └── backup/                    # 历史版本备份
├── database/                       # 数据库设计
│   └── Kline-Table-Event-Optimization.md
└── implementation/                 # 实现报告
    ├── REPORT-api-service-models-refactor.md
    └── REPORT-binance-service-models-refactor.md
```

## 阅读指南

### 新开发人员

1. **先读** `design/DATABASE_COORDINATED_ARCHITECTURE.md` - 理解系统设计思想
2. **再读** `design/QUANT_TRADING_SYSTEM_ARCHITECTURE.md` - 掌握实施细节
3. **然后** 按需阅读各服务模块设计文档

### 服务开发人员

- 开发新服务：参考现有服务设计文档（如 `03-binance-service.md`）
- WebSocket 相关：参考 `07-websocket-protocol.md` 系列文档
- API 模型：参考 `08-api-models.md`

### 快速查阅

- 任务调度 → `01-task-subscription.md`
- 数据流设计 → `02-dataflow.md`
- 交易功能 → `04-trading-orders.md`
- 告警功能 → `06-alert-service.md`

---

**版本**：v4.0
**更新**：2026-03-17
