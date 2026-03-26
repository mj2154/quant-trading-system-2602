# WebSocket API 协议规范

## 概述

本文档描述了量化交易系统的 **WebSocket API 协议规范**，采用**单一 WebSocket 连接**设计，所有请求（配置、搜索、K线、账户、告警等）都通过 WebSocket 消息完成。

本系统不仅为 TradingView 图表库提供数据服务，还支持账户实时订阅、告警管理、信号查询等多种功能。

**核心特性**:
- 纯 WebSocket 架构 - 无 REST API 端点
- 统一消息协议 - 所有请求/响应使用统一 JSON 格式
- 语义化交易对命名 - 采用 `EXCHANGE:SYMBOL[.后缀]` 格式
- 统一管理器 - UnifiedWebSocketManager 统一管理所有连接和订阅
- 多产品类型支持 - 现货、USDT永续合约
- 多交易所支持 - 通过统一消息格式支持不同交易所
- 实时性 - 所有请求和响应都是实时的

> **版本变更历史**: 详见 [07c-websocket-changelog.md](./07c-websocket-changelog.md)

---

## 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [WebSocket 端点](#websocket-端点)
- [语义化交易对命名规范](#语义化交易对命名规范)
- [统一消息协议](#统一消息协议)
- [心跳机制](#心跳机制)
- [前后端数据模型对齐说明](#前后端数据模型对齐说明)
- [参考资料](#参考资料)

### 相关子文档

| 文档 | 说明 |
|------|------|
| [07a-websocket-messages.md](./07a-websocket-messages.md) | **消息格式示例** - 仅包含 JSON 请求/响应示例，不包含数据模型定义 |
| [07b-websocket-errorcodes.md](./07b-websocket-errorcodes.md) | 错误码定义与说明 |
| [07c-websocket-changelog.md](./07c-websocket-changelog.md) | 协议版本变更历史 |
| [08-api-models.md](./08-api-models.md) | **数据模型设计** - 所有消息类型的 Pydantic 数据模型定义 |

> **重要**: 数据模型（Data Models）的设计统一放在 [08-api-models.md](./08-api-models.md) 中，07a-websocket-messages.md 仅用于展示 JSON 格式示例，便于快速理解和调试。

---

## 架构设计

### 核心原则：纯 WebSocket 架构

所有客户端与服务器的交互都通过**单一的 WebSocket 连接**完成：

```
┌─────────────────────────────────────────────────────────────────┐
│                    表示层 (Presentation Layer)                   │
│                     FastAPI + WebSocket 端点                     │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│              统一管理器层 (Unified Manager Layer)               │
│           UnifiedWebSocketManager - 统一连接和订阅管理           │
│                                                                  │
│           • 连接管理          • 订阅跟踪                         │
│           • 智能计算          • 消息路由                         │
│           • 状态监控          • 指标统计                         │
│           • 统一缓存          • 数据转换                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                   交易所服务层 (Exchange Service Layer)         │
│  binance_api_client (非实时)  +  binance_streams_client (实时)   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                   底层 (Underlying Layer)                       │
│                   币安 WebSocket 数据流                          │
└─────────────────────────────────────────────────────────────────┘
```

### 架构优势

1. **统一管理器** - 所有连接和订阅由 UnifiedWebSocketManager 统一管理
2. **智能订阅** - 自动计算、去重和优化订阅状态
3. **双客户端架构** - API 客户端（非实时）+ Streams 客户端（实时）
4. **统一缓存** - 交易所信息等数据统一缓存管理
5. **多交易所支持** - 通过统一消息格式支持不同交易所
6. **简化架构** - 无需维护多个 REST 端点

### 设计决策：借鉴币安WebSocket API风格

#### 问题背景

初始设计中存在概念混淆：
- **GET数据响应**: 使用 `action: "ack"` 返回实际数据
- **订阅确认**: 使用 `action: "ack"` 返回空确认
- 同一个 `ack` 概念既表示数据又表示确认，造成开发者困惑

#### 解决方案

参考币安WebSocket API的设计模式：
- **统一成功响应**: 使用 `type: "SUCCESS"`
- **语义清晰**: 通过 `type` 字段区分数据响应和确认消息
  - `type: "klines/config/search_symbols"` → 包含实际数据
  - `type: "subscribe/unsubscribe"` → 空data，仅确认

#### 设计优势

1. **语义清晰**: 开发者一眼就能区分数据响应和确认消息
2. **符合直觉**: `SUCCESS` 比 `ack` 更直观
3. **借鉴成熟设计**: 遵循币安WebSocket API简洁风格
4. **向后兼容**: 可平滑过渡，兼容旧版本客户端

### 保留的系统端点（仅 2 个）

| HTTP 方法 | 路径 | 功能描述 |
|-----------|------|----------|
| GET | `/` | 根路径，返回服务运行状态和版本信息 |
| GET | `/health` | 健康检查端点 |

### 命名约定

API 服务内部使用 **snake_case** 命名规范，与 Python 惯例一致：

| 层级 | 命名风格 | 说明 |
|------|----------|------|
| 内部服务 | snake_case | Python 惯例，如 `open_time`, `close_price` |
| 响应输出 | snake_case → camelCase | API 服务自动转换后发给前端 |

**转换机制**：使用 Pydantic v2 的 `to_camel` / `to_snake` 自动转换。

---

## WebSocket 端点

### 统一端点：所有功能

- **路径**: `/ws`
- **开发环境**: `ws://localhost:8000/ws`
- **生产环境**: `wss://your-domain.com/ws`
- **协议**: WebSocket (RFC 6455)
- **消息格式**: JSON
- **说明**: 单一 WebSocket 连接处理所有功能，通过消息类型区分市场数据和交易操作

### 状态查询

- **消息类型**: `STATUS`
- **用途**: 实时监控 WebSocket 服务状态
- **推送频率**: 每 5 秒

**状态推送消息格式**:
```json
{
    "type": "status_update",
    "data": {
        "metrics": {
            "active_connections": 5,
            "total_subscriptions": 12,
            "unique_symbols": 8,
            "exchange_subscriptions": {
                "BINANCE": 12
            }
        },
        "timestamp": 1703123456.789
    }
}
```

### 消息类型总览

| 消息类型 | 功能 |
|---------|------|
| **市场数据** | |
| `GET_CONFIG` | 获取图表配置 |
| `GET_SERVER_TIME` | 获取服务器时间 |
| `GET_METRICS` | 获取服务指标 |
| `GET_KLINES` | 获取K线数据 |
| `GET_SEARCH_SYMBOLS` | 搜索交易对 |
| `GET_RESOLVE_SYMBOL` | 解析交易对 |
| `GET_QUOTES` | 获取报价 |
| **订阅管理** | |
| `SUBSCRIBE` | 订阅数据 |
| `UNSUBSCRIBE` | 取消订阅 |
| **账户信息** | |
| `GET_FUTURES_ACCOUNT` | 获取期货账户信息 |
| `GET_SPOT_ACCOUNT` | 获取现货账户信息 |
| **交易操作** | |
| `CREATE_ORDER` | 创建订单 |
| `MODIFY_ORDER` | 修改订单 |
| `GET_ORDER` | 查询订单 |
| `LIST_ORDERS` | 查询订单列表 |
| `CANCEL_ORDER` | 取消订单 |
| `GET_OPEN_ORDERS` | 查询当前挂单 |
| **告警配置** | |
| `CREATE_ALERT_CONFIG` | 创建告警配置 |
| `LIST_ALERT_CONFIGS` | 列出告警配置 |
| `UPDATE_ALERT_CONFIG` | 更新告警配置（包含启用/禁用） |
| `DELETE_ALERT_CONFIG` | 删除告警配置 |
| **信号与策略** | |
| `LIST_SIGNALS` | 查询历史信号 |
| `GET_STRATEGY_METADATA` | 获取策略元数据列表 |
| `GET_STRATEGY_METADATA_BY_TYPE` | 获取指定策略元数据 |

**数据存储**：
- 交易请求写入 `order_tasks` 表（而非 `tasks` 表）
- 触发 `order_task_new` 通知给 binance-service 执行

> **消息类型详解**: 详见 [07a-websocket-messages.md](./07a-websocket-messages.md)
>
> **订单数据模型设计**: 详见 [08-api-models.md](./08-api-models.md)

---

## 语义化交易对命名规范

### 核心原则：前端无感知产品类型

系统采用订阅键格式 `EXCHANGE:SYMBOL@DATATYPE_RESOLUTION`，前端无需关心产品类型（现货/期货/期权），后端自动解析：

| 订阅键示例 | 交易所 | 产品类型 | 数据类型 | 分辨率 |
|-----------|--------|---------|---------|--------|
| `BINANCE:BTCUSDT@KLINE_60` | BINANCE | BTCUSDT | K线 | 60分钟 |
| `BINANCE:BTCUSDT@QUOTES` | BINANCE | BTCUSDT | 报价 | - |
| `BINANCE:FUTURES@USERDATA` | BINANCE | FUTURES | 用户数据 | - |
| `BINANCE:SPOT@USERDATA` | BINANCE | SPOT | 用户数据 | - |

### v2.0 订阅键格式规范

**格式**: `EXCHANGE:PRODUCT@DATATYPE[_RESOLUTION]`

- `EXCHANGE`: 交易所代码（大写）
- `PRODUCT`: 产品标识
  - 交易对（如 `BTCUSDT`、`BTCUSDT.PERP`）
  - 账户类型（如 `SPOT`、`FUTURES`）
- `DATATYPE`: 数据类型
  - `KLINE` - K线数据
  - `QUOTES` - 报价数据
  - `TRADE` - 成交数据
  - `USERDATA` - 用户数据
  - `SIGNAL` - 信号数据
- `RESOLUTION`: 分辨率（仅K线需要）
  - `1`, `3`, `5`, `15`, `30`, `60`, `120`, `240`, `360`, `480`, `720`
  - `D`, `1D`, `W`, `1W`, `M`, `1M`

**用户数据订阅键示例**:
- `BINANCE:SPOT@USERDATA` - 现货账户
- `BINANCE:FUTURES@USERDATA` - USDT本位合约账户

### 交易对搜索响应示例

```json
{
    "type": "SEARCH_SYMBOLS_DATA",
    "data": {
        "symbols": [
            {
                "symbol": "BINANCE:BTCUSDT",
                "fullName": "BINANCE:BTCUSDT",
                "description": "BTC/USDT",
                "exchange": "BINANCE",
                "ticker": "BTCUSDT",
                "type": "crypto"
            }
        ]
    }
}
```

---

## 统一消息协议

### 消息结构

所有 WebSocket 消息使用统一的 JSON 格式：

```json
{
    "protocolVersion": "2.0",
    "type": "MESSAGE_TYPE",
    "requestId": "uuid-string",
    "timestamp": 1234567890,
    "data": { }
}
```

### 顶层字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `protocolVersion` | string | ✅ | 协议版本号，当前为 `2.0` |
| `type` | string | ✅ | 消息类型，区分具体操作 |
| `requestId` | string | ✅ | 请求追踪ID，UUID格式 |
| `timestamp` | integer | ✅ | 时间戳（秒） |
| `data` | object | ✅ | 消息数据载荷 |

### 请求消息格式

```json
{
    "protocolVersion": "2.0",
    "type": "GET_KLINES",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456789,
    "data": {
        "symbol": "BINANCE:BTCUSDT",
        "interval": "60",
        "fromTime": 1703123456000,
        "toTime": 1703210000000
    }
}
```

### 三阶段消息流程

1. **请求阶段**: 客户端发送请求
2. **ACK 确认**: 服务端返回确认
3. **数据响应**: 服务端返回实际数据

> **详细消息格式**: 详见 [07a-websocket-messages.md](./07a-websocket-messages.md)

---

## 心跳机制

### 协议层 Ping-Pong

WebSocket 协议本身提供了 ping/pong 机制，浏览器会自动处理：

- **自动处理**: 浏览器 WebSocket API 自动响应 ping
- **透明管理**: 应用层无需感知心跳细节
- **推荐使用**: 协议层 ping/pong 是最佳实践

> **详细心跳机制说明**: 完整的Ping-Pong配置（Ping间隔20秒、超时60秒）、客户端实现、超时处理策略、JavaScript示例代码等详见 [07a-websocket-messages.md](./07a-websocket-messages.md#心跳机制ping-pong)

### 心跳检测

服务端定期推送状态信息：

```json
{
    "type": "status_update",
    "data": {
        "metrics": {
            "active_connections": 5,
            "total_subscriptions": 12
        },
        "timestamp": 1703123456.789
    }
}
```

---

## 前后端数据模型对齐说明

### 数据流

1. **外部数据进入**: 币安API → Binance模型 → 内部模型
2. **内部处理**: 使用 Pydantic 模型验证和转换
3. **输出给前端**: 内部模型 → CamelCase转换 → JSON

### 命名约定

| 场景 | 命名风格 | 示例 |
|------|---------|------|
| 外部API输入 | snake_case | `price_change`, `order_id` |
| 内部存储 | snake_case | `open_time`, `close_price` |
| API响应输出 | camelCase | `priceChange`, `orderId` |

### 模型基类

- **SnakeCaseModel**: 接收外部输入，自动将camelCase转为snake_case
- **CamelCaseModel**: 响应输出，序列化时自动转为camelCase

---

## 总结

本设计方案采用**纯 WebSocket 架构**，为 TradingView 图表库提供完整的数据服务。主要特点包括：

1. **统一管理器架构** - UnifiedWebSocketManager 统一管理所有连接和订阅
2. **双客户端架构** - API 客户端处理非实时数据 + Streams 客户端处理实时数据
3. **统一消息协议** - 所有请求/响应使用统一的 JSON 格式
4. **智能订阅管理** - 自动计算、去重和优化订阅状态
5. **实时数据推送** - 支持 K线、报价、成交、信号、账户增量推送
6. **多交易所支持** - 通过统一消息格式支持不同交易所

---

## User Data Stream Events Classification

用户数据流事件根据订阅键前缀分为以下两类：

### 现货用户数据流 (`BINANCE:SPOT@USERDATA`)

| 事件类型 | WS 事件名 | 说明 |
|---------|---------|------|
| `SpotAccountUpdate` | `ACCOUNT_UPDATE` | 账户余额/持仓变更 |
| `SpotBalanceUpdateEvent` | `BALANCE_UPDATE` | 余额变动事件 |
| `SpotExecutionReportEvent` | `EXECUTION_REPORT` | 订单执行报告 |

### 期货用户数据流 (`BINANCE:FUTURES@USERDATA`)

| 事件类型 | WS 事件名 | 说明 |
|---------|---------|------|
| `FuturesAccountUpdate` | `ACCOUNT_UPDATE` | 账户余额/持仓变更 |
| `FuturesOrderTradeUpdate` | `ORDER_TRADE_UPDATE` | 订单/成交更新 |

---

## 参考资料

- [08-api-models.md](./08-api-models.md) - API 数据模型定义
- [07a-websocket-messages.md](./07a-websocket-messages.md) - 消息类型详解
- [07b-websocket-errorcodes.md](./07b-websocket-errorcodes.md) - 错误码定义
- [07c-websocket-changelog.md](./07c-websocket-changelog.md) - 版本变更记录
