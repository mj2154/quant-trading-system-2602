# WebSocket API 协议规范

## 📋 概述

本文档描述了量化交易系统的 **WebSocket API 协议规范**，采用**单一 WebSocket 连接**设计，所有请求（配置、搜索、K线、账户、告警等）都通过 WebSocket 消息完成。

本系统不仅为 TradingView 图表库提供数据服务，还支持账户实时订阅、告警管理、信号查询等多种功能。

**v2.3 核心改进** (2026-03-02):
- 🚀 **交易功能支持** - 新增交易消息类型 (CREATE_ORDER, GET_ORDER, LIST_ORDERS, CANCEL_ORDER, GET_OPEN_ORDERS)
- 🚀 **订单数据推送** - 新增 ORDER_UPDATE 订阅类型，支持订单状态实时推送

**v2.2 核心改进** (2026-02-27):
- 🚀 **账户订阅支持** - 新增 ACCOUNT 订阅类型 (BINANCE:ACCOUNT@SPOT, BINANCE:ACCOUNT@FUTURES)
- 🚀 **增量数据推送** - 账户订阅采用"GET 完整 + 订阅增量"策略，前端需先 GET 初始化再订阅增量

**v2.1 核心改进** (2026-02-10):
- 🚀 **Ack 响应精简** - data 改为空对象 `{}`，移除冗余 message 字段
- 🚀 **命名区分** - 实时推送使用 `content`，避免与数据库 tasks 表的 payload 混淆

**v2.0 核心改进**：
- 🚀 **简洁订阅格式** - 使用订阅键直接表达数据需求，如 `BINANCE:BTCUSDT@KLINE_1`
- 🚀 **去除冗余字段** - 实时数据推送直接使用 TradingView 兼容格式
- 🚀 **简化API** - 订阅键直接编码数据类型和分辨率，无需额外字段
- 🚀 **大小写一致性** - 前端发送的订阅键与内部存储格式完全一致，无需大小写转换
- 🚀 **格式统一** - `type` 字段始终位于 `data` 内部，请求响应格式完全对称
- ✅ **纯 WebSocket 架构** - 无 REST API 端点，所有交互通过 WebSocket
- ✅ **统一消息协议** - 所有请求/响应使用统一 JSON 格式
- ✅ **语义化交易对命名** - 采用 `EXCHANGE:SYMBOL[.后缀]` 格式，支持现货、期货、期权等
- ✅ **统一管理器** - UnifiedWebSocketManager 统一管理所有连接和订阅
- ✅ **智能订阅** - 自动计算、去重和优化订阅状态
- ✅ **多产品类型支持** - 现货、USDT永续合约（期货仅支持永续）
- ✅ **多交易所支持** - 通过统一消息格式支持不同交易所
- ✅ **实时性** - 所有请求和响应都是实时的
- ✅ **简化架构** - 无需维护多个 REST 端点

---

## 📑 目录

- [概述](#-概述)
- [架构设计](#-架构设计)
- [WebSocket 端点](#-websocket-端点)
- [统一消息协议](#-统一消息协议)
  - [客户端请求](#-客户端请求)
  - [服务端响应](#-服务端响应)
  - [实时数据推送](#-实时数据推送)
- [消息类型详解](#-消息类型详解)
  - [GET 请求](#-get-请求)
  - [订阅/取消订阅](#-订阅-取消订阅)
  - [错误处理](#-错误处理)
- [语义化交易对命名规范](#-语义化交易对命名规范)
- [状态监控与心跳机制](#-状态监控与心跳机制)
- [错误处理](#-错误处理-1)
- [总结](#-总结)

---

## 🏗️ 架构设计

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
- **统一成功响应**: 使用 `action: "success"`
- **语义清晰**: 通过 `type` 字段区分数据响应和确认消息
  - `type: "klines/config/search_symbols"` → 包含实际数据
  - `type: "subscribe/unsubscribe"` → 空data，仅确认

#### 设计优势

1. **语义清晰**: 开发者一眼就能区分数据响应和确认消息
2. **符合直觉**: `success` 比 `ack` 更直观
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

```python
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

class KlineResponse(BaseModel):
    """API 响应模型 - 序列化时自动转为 camelCase"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    open_time: int        # 内部使用 snake_case
    # 序列化后: "openTime": 1234567890
```

> **详细设计**：见 [DATABASE_COORDINATED_ARCHITECTURE.md](./DATABASE_COORDINATED_ARCHITECTURE.md#44-数据命名规范)

---

## 🌐 WebSocket 端点

### 主端点：数据通道

- **路径**: `/ws/market`
- **开发环境**: `ws://localhost:8000/ws/market`
- **生产环境**: `wss://your-domain.com/ws/market`
- **协议**: WebSocket (RFC 6455)
- **消息格式**: JSON

### 状态监控端点

- **路径**: `/ws/market/status`
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

### 心跳机制（Ping-Pong）

本系统采用 **Uvicorn 服务器级别自动 ping/pong** 机制，与币安 WebSocket API 保持完全一致。

#### 技术实现方案

**服务器配置**：
- **Ping 间隔**: 20 秒
- **Ping 超时**: 60 秒（1 分钟）
- **实现方式**: Uvicorn ASGI 服务器自动处理（--ws-ping-interval 20 --ws-ping-timeout 60）

#### 工作机制

```
时间线示例：
T+0s   : WebSocket 连接建立
T+20s  : 服务器发送第一个 ping frame
T+40s  : 服务器发送第二个 ping frame
T+60s  : 服务器发送第三个 ping frame
T+80s  : 如果前面所有 ping 都超时，连接自动断开
```

#### 客户端要求

**必须支持**：
- ✅ 自动响应服务器 ping frame（发送 pong）
- ✅ 60 秒内响应所有 ping
- ✅ 支持 unsolicited pong（主动发送 pong）

**建议实现**（JavaScript 示例）：
```javascript
// 大多数浏览器 WebSocket API 会自动处理 ping/pong
const ws = new WebSocket('wss://your-domain.com/ws/market');

ws.onopen = () => {
    console.log('WebSocket connected');
    // 浏览器会自动响应服务器的 ping
};

ws.onmessage = (event) => {
    // 处理业务消息
    // 注意：ping/pong 是协议层，浏览器不会暴露给应用层
};

ws.onclose = (event) => {
    // 连接关闭
    if (event.code === 1006) {
        // 代码 1006 表示异常关闭（可能是 ping 超时）
        console.log('Connection lost due to ping timeout');
    }
};

// 可选：应用层心跳监控（不影响协议层 ping/pong）
let lastMessageTime = Date.now();
setInterval(() => {
    if (Date.now() - lastMessageTime > 60000) {
        console.warn('No messages received for 60s, connection may be dead');
    }
}, 10000);

ws.onmessage = (event) => {
    lastMessageTime = Date.now();
    // 处理业务消息...
};
```

#### 超时处理策略

| 场景 | 客户端行为 | 建议处理 |
|------|------------|----------|
| **正常情况** | 正常响应 ping | 连接保持 |
| **网络波动** | 偶尔丢包，60秒内恢复 | 连接保持（容忍 1-2 次丢包） |
| **死连接** | 60秒内无响应 | 服务器自动断开，客户端应实现重连 |
| **客户端主动断开** | 发送 close frame | 正常断开流程 |

#### 优势

1. **零开发成本** - 协议层自动处理，无需应用层实现
2. **性能最优** - Uvicorn 优化的 C 实现，低延迟
3. **标准兼容** - 与币安 WebSocket API 机制一致
4. **透明管理** - 应用层无需感知心跳细节
5. **自动恢复** - 检测到死连接自动断开，避免资源泄露

#### 监控与调试

**服务器端监控**：
- 查看 Uvicorn 日志中的 ping/pong 记录
- 监控连接断开原因（代码 1006 表示 ping 超时）

**客户端调试**：
- 监听 `onclose` 事件，检查 `event.code`
- 代码 1006 通常表示 ping 超时
- 建议实现自动重连逻辑

#### 与应用层心跳的区别

| 特性 | 协议层 ping/pong（推荐） | 应用层心跳 |
|------|--------------------------|------------|
| **实现位置** | Uvicorn 服务器 | 应用代码 |
| **开发成本** | 零 | 中等 |
| **性能开销** | 极低 | 低 |
| **可控性** | 低（自动） | 高（自定义） |
| **兼容性** | 标准 WebSocket | 需要自定义协议 |
| **币安一致性** | ✅ 完全一致 | ⚠️ 不同 |

**结论**：推荐使用协议层 ping/pong，与币安保持一致，零开发成本，性能最优。

---

## 🏷️ 语义化交易对命名规范

### 核心原则：前端无感知产品类型

前端只关心能否获取历史数据和订阅实时数据，**不关心底层是现货、期货还是其他产品类型**。后端负责将语义化的交易对名称转换为对应交易所的API格式。

### v2.0 订阅键格式规范

#### 基础格式

```
{EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]
```

#### 格式示例

**现货交易**：
- `BINANCE:BTCUSDT@KLINE_1` - 1分钟K线 (TV分辨率: "1")
- `BINANCE:BTCUSDT@KLINE_60` - 1小时K线 (TV分辨率: "60")
- `BINANCE:BTCUSDT@KLINE_D` - 1天K线 (TV分辨率: "D")
- `BINANCE:BTCUSDT@TICKER` - 实时报价
- `BINANCE:BTCUSDT@TRADE` - 实时交易

**永续合约**：
- `BINANCE:BTCUSDT.PERP@KLINE_1` - 永续合约1分钟K线 (TV分辨率: "1")
- `BINANCE:BTCUSDT.PERP@KLINE_60` - 永续合约1小时K线 (TV分辨率: "60")
- `BINANCE:BTCUSDT.PERP@TICKER` - 永续合约实时报价

> **注意**: 本系统仅支持永续合约期货交易，季度期货已被移除

#### 分辨率格式规则

TV 图表库支持的分辨率格式如下：

| 类型 | 格式 | 可省略形式 | 示例 |
|------|------|-----------|------|
| 天级 | `xD` | `D` (=`1D`) | `1D`, `2D`, `3D`, `D` |
| 周级 | `xW` | `W` (=`1W`) | `1W`, `2W`, `W` |
| 月级 | `xM` | `M` (=`1M`) | `1M`, `3M`, `M` |

**说明**:
- 当单位数量等于 1 时，可以省略数字。例如 `D` = `1D`，`W` = `1W`，`M` = `1M`
- **年级分辨率不能用 `Y` 表示**，必须用 `12M`（12个月 = 1年）

#### TV分辨率映射表

| TV分辨率 | 说明 | 币安间隔 | 支持状态 |
|----------|------|----------|----------|
| **秒级时间周期** |
| `1s` | 1秒 | `1s` | 🔶 预留（币安不支持） |
| `5s` | 5秒 | `5s` | 🔶 预留（币安不支持） |
| `10s` | 10秒 | `10s` | 🔶 预留（币安不支持） |
| `15s` | 15秒 | `15s` | 🔶 预留（币安不支持） |
| `30s` | 30秒 | `30s` | 🔶 预留（币安不支持） |
| **分钟级时间周期** |
| `1` | 1分钟 | `1m` | ✅ 支持 |
| `3` | 3分钟 | `3m` | ✅ 支持 |
| `5` | 5分钟 | `5m` | ✅ 支持 |
| `15` | 15分钟 | `15m` | ✅ 支持 |
| `30` | 30分钟 | `30m` | ✅ 支持 |
| `45` | 45分钟 | `45m` | ✅ 支持 |
| `60` | 1小时 | `1h` | ✅ 支持 |
| `120` | 2小时 | `2h` | ✅ 支持 |
| `240` | 4小时 | `4h` | ✅ 支持 |
| `360` | 6小时 | `6h` | ✅ 支持 |
| `480` | 8小时 | `8h` | ✅ 支持 |
| `720` | 12小时 | `12h` | ✅ 支持 |
| **天级时间周期** |
| `D` | 1天 | `1d` | ✅ 支持 |
| `1D` | 1天（别名） | `1d` | ✅ 支持 |
| `2D` | 2天 | `2d` | 🔶 预留（币安不支持） |
| `3D` | 3天 | `3d` | ✅ 支持 |
| `4D` | 4天 | `4d` | 🔶 预留（币安不支持） |
| `5D` | 5天 | `5d` | 🔶 预留（币安不支持） |
| `7D` | 7天 | `7d` | 🔶 预留（币安不支持） |
| **周级时间周期** |
| `W` | 1周 | `1w` | ✅ 支持 |
| `2W` | 2周 | `2w` | 🔶 预留（币安不支持） |
| **月级时间周期** |
| `M` | 1月 | `1M` | ✅ 支持 |
| `3M` | 3月 | `3M` | 🔶 预留（币安不支持） |
| `6M` | 6月 | `6M` | 🔶 预留（币安不支持） |
| `9M` | 9月 | `9M` | 🔶 预留（币安不支持） |
| `12M` | 12月 | `12M` | ✅ 支持 |
| **年级时间周期** |
| `12M` | 1年 | `12M` | 🔶 预留（币安不支持） |
| `24M` | 2年 | `24M` | 🔶 预留（币安不支持） |
| `36M` | 3年 | `36M` | 🔶 预留（币安不支持） |
| `60M` | 5年 | `60M` | 🔶 预留（币安不支持） |
| `120M` | 10年 | `120M` | 🔶 预留（币安不支持） |

> **说明**: TV 图表库不支持 `Y` 格式表示年份，年级分辨率必须用 `xM` 格式（月份）。例如 `12M` = 1年，`24M` = 2年。

**说明**:
- ✅ **支持**: 币安API原生支持，可正常获取数据
- 🔶 **预留**: 暂不支持，为未来扩展保留映射关系 |

#### v1.0 格式兼容性说明

v2.0 完全不兼容 v1.0 格式。前端需要使用新的订阅键格式。

**v1.0 旧格式**（已废弃）：
```json
{
    "subscriptions": {
        "kline": [
            {"symbol": "BINANCE:BTCUSDT", "interval": "1"}
        ]
    }
}
```

**v2.0 新格式**：
```json
{
    "subscriptions": [
        "BINANCE:BTCUSDT@KLINE_1",
        "BINANCE:BTCUSDT.PERP@KLINE_1"
    ]
}
```

### 传统交易对格式（用于历史数据查询）

```
基础格式: EXCHANGE:SYMBOL[.后缀]

现货: BINANCE:BTCUSDT
永续合约 (USDⓈ-M): BINANCE:BTCUSDT.PERP
```

### 格式转换说明

> **重要**: 内部统一格式与交易所API格式可能不同，系统会自动进行转换。

永续合约格式转换示例:
- **内部统一格式**: `BINANCE:BTCUSDT.PERP`
- **币安API格式**: `BTCUSDT_PERPETUAL`

系统会在以下位置自动转换：
1. **缓存初始化时**: 将交易所API格式转换为内部统一格式存储
2. **数据查询时**: 将内部统一格式转换为交易所API格式调用

### 完整产品类型支持

| 产品类型 | 命名格式 | 示例 | 币安API端点 |
|---------|----------|------|-------------|
| **现货** | `EXCHANGE:SYMBOL` | `BINANCE:BTCUSDT` | `/api/v3/klines` |
| **永续合约 (USDⓈ-M)** | `EXCHANGE:SYMBOL.PERP` | `BINANCE:BTCUSDT.PERP` | `/fapi/v1/continuousKlines` |

### 交易对搜索响应示例

```json
{
    "protocolVersion": "2.0",
    "type": "CONFIG_DATA",
    "requestId": "req_1703123456789_002",
    "timestamp": 1703123456790,
    "data": {
        "type": "search_symbols",
        "symbols": [
            {
                "symbol": "BINANCE:BTCUSDT",
                "full_name": "BINANCE:BTCUSDT",
                "description": "比特币/泰达币 (现货)",
                "exchange": "BINANCE",
                "ticker": "BTCUSDT",
                "type": "crypto"
            },
            {
                "symbol": "BINANCE:BTCUSDT.PERP",
                "full_name": "BINANCE:BTCUSDT.PERP",
                "description": "比特币/泰达币永续合约",
                "exchange": "BINANCE",
                "ticker": "BTCUSDT.PERP",
                "type": "crypto"
            },
            {
                "symbol": "BINANCE:BTCUSDT.20260327",
                "full_name": "BINANCE:BTCUSDT.20260327",
                "description": "比特币/泰达币2026年3月27日期货",
                "exchange": "BINANCE",
                "ticker": "BTCUSDT.20260327",
                "type": "crypto"
            }
        ],
        "total": 3,
        "count": 3
    }
}
```

### 前端使用示例

```javascript
// 获取永续合约历史数据
const historyRequest = {
    "protocolVersion": "2.0",
    "type": "GET_KLINES",
    "requestId": "history_futures_001",
    "timestamp": Date.now(),
    "data": {
        "symbol": "BINANCE:BTCUSDT.PERP",  // 前端使用语义化名称
        "interval": "60",
        "limit": 500
    }
};

// 订阅永续合约实时数据
const subscribeRequest = {
    "protocolVersion": "2.0",
    "type": "SUBSCRIBE",
    "requestId": "sub_futures_001",
    "timestamp": Date.now(),
    "data": {
        "subscriptions": [
            "BINANCE:BTCUSDT.PERP@KLINE_60"
        ]
        }
    }
};
```

**重要**: 前端**无需知道**底层是永续合约还是现货，只需要使用后端提供的交易对名称即可！

---

## 📡 统一消息协议

> **重要更新**: 本协议采用**信封式设计**，统一消息类型系统。详细类型枚举定义见上节。

### 消息结构

本协议采用**信封式设计**，所有数据包都包含统一的顶层字段：

| 类别 | 类型名称 | 说明 |
|------|---------|------|
| **请求类型** | | |
| | `GET_KLINES` | 获取K线历史数据 |
| | `GET_QUOTES` | 批量获取报价 |
| | `GET_CONFIG` | 获取数据源配置 |
| | `GET_SERVER_TIME` | 获取服务器时间 |
| | `GET_SEARCH_SYMBOLS` | 搜索交易对 |
| | `GET_RESOLVE_SYMBOL` | 获取交易对详情 |
| | `GET_SUBSCRIPTIONS` | 查询当前订阅 |
| | `GET_SPOT_ACCOUNT` | 获取现货账户信息 |
| | `GET_FUTURES_ACCOUNT` | 获取期货账户信息 |
| | `SUBSCRIBE` | 订阅实时数据 |
| | `UNSUBSCRIBE` | 取消订阅 |
| | `CREATE_ALERT_CONFIG` | 创建告警配置 |
| | `LIST_ALERT_CONFIGS` | 列出告警配置 |
| | `UPDATE_ALERT_CONFIG` | 更新告警配置 |
| | `DELETE_ALERT_CONFIG` | 删除告警配置 |
| | `ENABLE_ALERT_CONFIG` | 启用告警配置 |
| | `LIST_SIGNALS` | 查询历史信号 |
| | `GET_STRATEGY_METADATA` | 获取策略元数据列表 |
| | `GET_STRATEGY_METADATA_BY_TYPE` | 获取指定策略元数据 |
| **交易类型** | | |
| | `CREATE_ORDER` | 创建订单 |
| | `GET_ORDER` | 查询单个订单 |
| | `LIST_ORDERS` | 查询订单列表 |
| | `CANCEL_ORDER` | 撤销订单 |
| | `GET_OPEN_ORDERS` | 查询当前挂单 |
| **响应类型** | | |
| | `ACK` | 请求确认（第一阶段） |
| | `ERROR` | 错误响应 |
| | `UPDATE` | 实时数据推送 |
| **数据类型** | | |
| | `KLINES_DATA` | K线数据 |
| | `QUOTES_DATA` | 报价数据 |
| | `CONFIG_DATA` | 配置数据 |
| | `SERVER_TIME_DATA` | 服务器时间数据 |
| | `SYMBOL_DATA` | 交易对详情数据 |
| | `SEARCH_SYMBOLS_DATA` | 搜索结果数据 |
| | `SUBSCRIPTION_DATA` | 订阅确认数据 |
| | `ACCOUNT_DATA` | 账户数据 |
| | `ALERT_CONFIG_DATA` | 告警配置数据 |
| | `SIGNAL_DATA` | 信号数据 |
| | `STRATEGY_METADATA_DATA` | 策略元数据数据 |
| | `ORDER_DATA` | 订单数据 |
| | `ORDER_LIST_DATA` | 订单列表数据 |
| | `ORDER_UPDATE` | 订单更新推送 |

> **重要说明**: 最终 SUCCESS 响应的 `type` 字段值为**数据类型**（如 `KLINES_DATA`），而非 `SUCCESS`。`SUCCESS` 仅用于表示响应分类概念，实际类型使用具体的数据类型。

### 顶层字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|-----|------|
| `protocolVersion` | string | 是 | 协议版本（如 `2.0`） |
| `type` | string | 是 | 消息类型，如 `GET_KLINES`, `SUCCESS`, `ACK`, `UPDATE` |
| `requestId` | string | 否 | 请求ID，请求/响应必填，推送可省略 |
| `timestamp` | long | 是 | Unix 时间戳（**毫秒**，13位数字，如 `1704067200000`） |
| `data` | object | 是 | 消息数据内容 |

### 请求消息格式

```json
{
    "protocolVersion": "2.0",
    "type": "GET_KLINES",
    "requestId": "req_xxx",
    "timestamp": 1234567890,
    "data": {
        "symbol": "BTCUSDT",
        "interval": "60",
        "fromTime": 1704067200000,
        "toTime": 1706745600000
    }
}
```

**确认消息（服务端 → 客户端，异步任务第一阶段）**:
```json
{
    "protocolVersion": "2.0",
    "type": "ACK",
    "requestId": "req_xxx",
    "timestamp": 1234567890,
    "data": {}
}
```

**成功响应消息（服务端 → 客户端）**:
```json
{
    "protocolVersion": "2.0",
    "type": "KLINES_DATA",
    "requestId": "req_xxx",
    "timestamp": 1234567890,
    "data": {
        "symbol": "BTCUSDT",
        "interval": "60",
        "bars": [...],
        "count": 100
    }
}
```

**错误响应消息（服务端 → 客户端）**:
```json
{
    "protocolVersion": "2.0",
    "type": "ERROR",
    "requestId": "req_xxx",
    "timestamp": 1234567890,
    "data": {
        "errorCode": "INVALID_SYMBOL",
        "errorMessage": "交易对不存在"
    }
}
```

**更新消息（服务端 → 客户端，实时数据推送）**:
```json
{
    "protocolVersion": "2.0",
    "type": "UPDATE",
    "timestamp": 1234567890,
    "data": {
        "subscriptionKey": "BINANCE:BTCUSDT@KLINE_1",
        "bar": {...}
    }
}
```

#### requestId 与 taskId 的区别

| 字段 | 来源 | 用途 | 是否返回客户端 |
|------|------|------|--------------|
| `requestId` | 客户端生成 | 关联请求和最终响应 | ✅ 是 |
| `taskId` | 服务端生成 | 内部任务管理与数据库映射 | ❌ 否 |

**重要说明**：
- `requestId`：客户端生成，用于追踪整个请求-响应流程
- `taskId`：服务端生成，仅用于内部任务管理和数据库映射，**不返回给客户端**
- 更新消息（update）是服务器主动推送的数据，遵循 TradingView API 规范，不包含 requestId 字段

### 三阶段消息流程

> **重要设计原则**：本系统**所有请求类型**都遵循"先返回 ack，确认收到请求"的原则。

```
请求 → ack确认 → (处理) → success/error回应
```

**三个阶段**：

| 阶段 | type | 说明 |
|------|------|------|
| 1 | `GET_XXX`/`SUBSCRIBE`/`UNSUBSCRIBE` | 客户端发送请求（携带 requestId） |
| 2 | `ACK` | **服务端立即确认收到请求**（返回 requestId） |
| 3 | `SUCCESS`/`ERROR` | 服务端返回处理结果（返回 requestId） |

**适用范围**：本系统**所有请求类型**都采用三阶段模式，包括：
- 直接查询操作：`GET_CONFIG`、`GET_QUOTES`
- 异步任务操作：`GET_KLINES`、`GET_SERVER_TIME`
- 订阅操作：`SUBSCRIBE`、`UNSUBSCRIBE`

无论数据来源于本地查询还是远程 API 处理，都必须先返回 ACK 确认收到请求。

### 消息类型总览

| type | 方向 | 用途 |
|------|------|------|
| `GET_KLINES` | 客户端→服务端 | 获取K线历史数据 |
| `GET_QUOTES` | 客户端→服务端 | 批量获取报价 |
| `GET_CONFIG` | 客户端→服务端 | 获取数据源配置 |
| `GET_SERVER_TIME` | 客户端→服务端 | 获取服务器时间 |
| `SUBSCRIBE` | 客户端→服务端 | 订阅实时数据 |
| `UNSUBSCRIBE` | 客户端→服务端 | 取消订阅 |
| `ACK` | 服务端→客户端 | 确认收到请求（返回 requestId） |
| `UPDATE` | 服务端→客户端 | 数据推送（实时数据，不返回 requestId） |
| `ERROR` | 服务端→客户端 | 错误消息（返回 requestId） |

> **重要说明**: 最终成功响应的 `type` 字段使用**数据类型**（如 `KLINES_DATA`），而非 `SUCCESS`。成功响应通过具体数据类型区分请求类型。

**设计说明：请求与响应的类型区分**

为避免请求与响应混淆，采用以下命名规则：
- **请求类型**：使用动作前缀（如 `GET_`、`SUBSCRIBE`）表示客户端动作
- **响应类型**：使用 `_DATA` 后缀表示返回的数据内容

前端收到响应后，通过 `requestId` 关联原始请求，无需依赖 `type` 字段判断请求类型。

**请求类型与数据类型映射**:
| 请求类型 | 响应数据类型 | 说明 |
|----------|-------------|------|
| `GET_KLINES` | `KLINES_DATA` | K线历史数据 |
| `GET_QUOTES` | `QUOTES_DATA` | 报价数据 |
| `GET_CONFIG` | `CONFIG_DATA` | 数据源配置 |
| `GET_SERVER_TIME` | `SERVER_TIME_DATA` | 服务器时间 |
| `GET_SEARCH_SYMBOLS` | `SEARCH_SYMBOLS_DATA` | 搜索结果数据 |
| `GET_RESOLVE_SYMBOL` | `SYMBOL_DATA` | 交易对详情数据 |
| `GET_SUBSCRIPTIONS` | `SUBSCRIPTION_DATA` | 当前订阅列表 |
| `GET_SPOT_ACCOUNT` | `ACCOUNT_DATA` | 现货账户信息 |
| `GET_FUTURES_ACCOUNT` | `ACCOUNT_DATA` | 期货账户信息 |
| `SUBSCRIBE` | `SUBSCRIPTION_DATA` | 订阅确认 |
| `UNSUBSCRIBE` | `SUBSCRIPTION_DATA` | 取消订阅确认 |
| `CREATE_ALERT_CONFIG` | `ALERT_CONFIG_DATA` | 告警配置 |
| `LIST_ALERT_CONFIGS` | `ALERT_CONFIG_DATA` | 告警配置列表 |
| `UPDATE_ALERT_CONFIG` | `ALERT_CONFIG_DATA` | 告警配置更新结果 |
| `DELETE_ALERT_CONFIG` | `ALERT_CONFIG_DATA` | 告警配置删除结果 |
| `ENABLE_ALERT_CONFIG` | `ALERT_CONFIG_DATA` | 告警配置启用结果 |
| `LIST_SIGNALS` | `SIGNAL_DATA` | 信号数据列表 |
| `GET_STRATEGY_METADATA` | `STRATEGY_METADATA_DATA` | 策略元数据列表 |
| `GET_STRATEGY_METADATA_BY_TYPE` | `STRATEGY_METADATA_DATA` | 指定策略元数据 |

**账户信息类型**（需要认证）:
| type | 说明 | 用途 |
|------|------|------|
| `GET_FUTURES_ACCOUNT` | 获取期货账户信息 | 查询 U 本位合约账户余额、持仓、保证金等 |
| `GET_SPOT_ACCOUNT` | 获取现货账户信息 | 查询现货账户余额、手续费率等 |

> **透传模式说明**: 账户信息采用"透传"模式，不同于其他类型由 api-service 处理。账户信息由 binance-service 直接从 Binance API 获取原始数据，存储到 `account_info` 表，api-service 直接从数据库读取并透传给前端，前端负责解析完整字段。这种方式避免了大数据量在服务间传递，减少延迟。

**交易类型**（binance-service）:
| type | 响应类型 | 说明 |
|------|---------|------|
| `CREATE_ORDER` | `ORDER_DATA` | 创建订单 |
| `GET_ORDER` | `ORDER_DATA` | 查询单个订单 |
| `LIST_ORDERS` | `ORDER_LIST_DATA` | 查询订单列表 |
| `CANCEL_ORDER` | `ORDER_DATA` | 撤销订单 |
| `GET_OPEN_ORDERS` | `ORDER_LIST_DATA` | 查询当前挂单 |

> **交易功能说明**: 交易功能通过trading_orders表实现。API服务接收WebSocket请求后写入trading_orders表，触发notify_order_new()通知binance-service执行实际下单操作。订单状态更新通过binance-service监听WebSocket用户数据流实现，详见 [04-trading-orders.md](./04-trading-orders.md)。

**告警配置类型**（signal-service）:
| type | 说明 | 用途 |
|------|------|------|
| `CREATE_ALERT_CONFIG` | 创建告警配置 | 设置信号策略和参数 |
| `LIST_ALERT_CONFIGS` | 列出告警配置 | 查询/筛选用户的告警 |
| `UPDATE_ALERT_CONFIG` | 更新告警配置 | 修改告警配置 |
| `DELETE_ALERT_CONFIG` | 删除告警配置 | 移除告警 |
| `ENABLE_ALERT_CONFIG` | 启用告警配置 | 激活告警 |
| `LIST_SIGNALS` | 查询历史信号 | 获取信号计算结果 |

**策略元数据类型**（api-service）:
| type | 说明 | 用途 |
|------|------|------|
| `GET_STRATEGY_METADATA` | 获取所有策略元数据 | 获取已注册策略列表及其参数定义 |
| `GET_STRATEGY_METADATA_BY_TYPE` | 获取指定策略元数据 | 根据策略类型获取详细参数定义 |

---

## 💬 消息类型详解

### 客户端请求

#### 1. GET 请求

所有获取数据的操作都统一使用顶层 `type` 字段区分具体操作类型（如 `GET_KLINES`、`GET_CONFIG` 等）。

##### 1.1 获取数据源配置

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_CONFIG",
    "requestId": "req_1703123456789_001",
    "timestamp": 1703123456789,
    "data": {}
}
```

**说明**:
- 对应 TradingView 的 `onReady` 方法
- 用于初始化图表库，获取支持的功能配置

---

##### 1.2 搜索交易对

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_SEARCH_SYMBOLS",
    "requestId": "req_1703123456789_002",
    "timestamp": 1703123456789,
    "data": {
        "query": "BTC",
        "exchange": "BINANCE",
        "symbolType": "crypto",
        "limit": 50,
        "offset": 0
    }
}
```

**字段说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 否 | 搜索关键词 |
| `exchange` | string | 否 | 交易所代码 |
| `symbolType` | string | 否 | 标的类型 |
| `limit` | integer | 否 | 返回数量限制（默认50，最大100） |
| `offset` | integer | 否 | 分页偏移量（默认0） |

**说明**:
- 对应 TradingView 的 `searchSymbols` 方法
- 用于搜索交易对列表

---

##### 1.3 获取交易对详情

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_RESOLVE_SYMBOL",
    "requestId": "req_1703123456789_003",
    "timestamp": 1703123456789,
    "data": {
        "symbol": "BINANCE:BTCUSDT"
    }
}
```

**字段说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | ✅ | 固定为 `resolve_symbol` |
| `symbol` | string | ✅ | 标的全名，格式：`EXCHANGE:SYMBOL` |

**说明**:
- 对应 TradingView 的 `resolveSymbol` 方法
- 用于获取交易对的详细信息

**完整响应示例**:
```json
{
    "protocolVersion": "2.0",
    "type": "SYMBOL_DATA",
    "requestId": "req_1703123456789_003",
    "timestamp": 1703123456790,
    "data": {
        "symbol": "BTCUSDT",
        "name": "BTCUSDT",
        "base_name": ["NASDAQ:AAPL"],
        "ticker": "BINANCE:BTCUSDT",
        "description": "BTC/USDT",
        "long_description": "比特币/泰达币 (现货)",
        "type": "crypto",
        "session": "24x7",
        "session_display": "24小时",
        "session_holidays": "",
        "corrections": "",
        "exchange": "BINANCE",
        "listed_exchange": "BINANCE",
        "timezone": "Etc/UTC",
        "format": "price",
        "minmov": 1.0,
        "pricescale": 100,
        "minmove2": 0,
        "fractional": false,
        "variable_tick_size": "0.01 10 0.02 25 0.05",
        "has_intraday": true,
        "has_seconds": false,
        "has_ticks": false,
        "has_daily": true,
        "has_weekly_and_monthly": true,
        "supported_resolutions": ["1", "5", "15", "60", "240", "1D", "1W", "1M"],
        "intraday_multipliers": ["1", "5", "15", "60"],
        "seconds_multipliers": null,
        "daily_multipliers": ["1"],
        "weekly_multipliers": ["1"],
        "monthly_multipliers": ["1"],
        "build_seconds_from_ticks": false,
        "has_empty_bars": false,
        "visible_plots_set": "ohlcv",
        "volume_precision": 8,
        "data_status": "streaming",
        "delay": 0,
        "currency_code": "USDT",
        "original_currency_code": "USDT",
        "unit_id": "",
        "original_unit_id": "",
        "sector": "Technology",
        "industry": "Cryptocurrency",
        "expired": false,
        "expiration_date": null,
        "logo_urls": ["https://assets.coingecko.com/coins/images/1/large/bitcoin.png"]
    }
}
```

---

##### 1.4 获取 K 线数据

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_KLINES",
    "requestId": "req_1703123456789_004",
    "timestamp": 1703123456789,
    "data": {
        "symbol": "BINANCE:BTCUSDT",
        "interval": "60",
        "fromTime": 1703123456000,
        "toTime": 1703210000000
    }
}
```

**字段说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | string | ✅ | 标的全名，格式：`EXCHANGE:SYMBOL` |
| `interval` | string | ✅ | K线周期（如 `1`, `5`, `60`, `1D`，与数据库字段一致） |
| `fromTime` | integer | ✅ | 开始时间戳（毫秒） |
| `toTime` | integer | ✅ | 结束时间戳（毫秒） |

**周期映射**:
| 前端周期 | 说明 | 币安间隔 | 支持状态 |
|----------|------|----------|----------|
| **秒级时间周期** |
| `1s` | 1秒 | `1s` | 🔶 预留（币安不支持） |
| `5s` | 5秒 | `5s` | 🔶 预留（币安不支持） |
| `10s` | 10秒 | `10s` | 🔶 预留（币安不支持） |
| `15s` | 15秒 | `15s` | 🔶 预留（币安不支持） |
| `30s` | 30秒 | `30s` | 🔶 预留（币安不支持） |
| **分钟级时间周期** |
| `1` | 1分钟 | `1m` | ✅ 支持 |
| `3` | 3分钟 | `3m` | ✅ 支持 |
| `5` | 5分钟 | `5m` | ✅ 支持 |
| `15` | 15分钟 | `15m` | ✅ 支持 |
| `30` | 30分钟 | `30m` | ✅ 支持 |
| `45` | 45分钟 | `45m` | ✅ 支持 |
| `60` | 1小时 | `1h` | ✅ 支持 |
| `120` | 2小时 | `2h` | ✅ 支持 |
| `240` | 4小时 | `4h` | ✅ 支持 |
| `360` | 6小时 | `6h` | ✅ 支持 |
| `480` | 8小时 | `8h` | ✅ 支持 |
| `720` | 12小时 | `12h` | ✅ 支持 |
| **天级时间周期** |
| `D` | 1天 | `1d` | ✅ 支持 |
| `1D` | 1天（别名） | `1d` | ✅ 支持 |
| `2D` | 2天 | `2d` | 🔶 预留（币安不支持） |
| `3D` | 3天 | `3d` | ✅ 支持 |
| `4D` | 4天 | `4d` | 🔶 预留（币安不支持） |
| `5D` | 5天 | `5d` | 🔶 预留（币安不支持） |
| `7D` | 7天 | `7d` | 🔶 预留（币安不支持） |
| **周级时间周期** |
| `W` | 1周 | `1w` | ✅ 支持 |
| `2W` | 2周 | `2w` | 🔶 预留（币安不支持） |
| **月级时间周期** |
| `M` | 1月 | `1M` | ✅ 支持 |
| `3M` | 3月 | `3M` | 🔶 预留（币安不支持） |
| `6M` | 6月 | `6M` | 🔶 预留（币安不支持） |
| `9M` | 9月 | `9M` | 🔶 预留（币安不支持） |
| `12M` | 12月 | `12M` | ✅ 支持 |
| **年级时间周期** |
| `12M` | 1年 | `12M` | 🔶 预留（币安不支持） |
| `24M` | 2年 | `24M` | 🔶 预留（币安不支持） |
| `36M` | 3年 | `36M` | 🔶 预留（币安不支持） |
| `60M` | 5年 | `60M` | 🔶 预留（币安不支持） |
| `120M` | 10年 | `120M` | 🔶 预留（币安不支持） |

> **说明**: TV 图表库不支持 `Y` 格式表示年份，年级分辨率必须用 `xM` 格式（月份）。例如 `12M` = 1年，`24M` = 2年。

**说明**:
- ✅ **支持**: 币安API原生支持，可正常获取数据
- 🔶 **预留**: 暂不支持，为未来扩展保留映射关系
- 对应 TradingView 的 `getBars` 方法
- 用于获取 K 线历史数据

**异步任务三阶段流程**:

```
1. 客户端发送请求
2. 服务端返回 ack 确认（返回 requestId）
3. 服务端异步处理完成后返回 success（返回 requestId 和 klines 数据）
```

**缓存查询策略（重要设计）**:

> **⚠️ 核心优化点：避免重复调用币安 API**
>
> K线历史数据查询遵循以下策略，**每次重构都必须保持此逻辑**：

**处理流程**:
```
1. api-service 接收前端请求
   ↓
2. 根据周期对齐时间（from_time, to_time）
   ↓
3. 查询 klines_history 表，验证起始和结束两个端点的数据
   ↓
4. 判断逻辑：
   ├── 起始端点存在 AND 结束端点存在 → 直接从数据库返回（不走异步任务）
   └── 任意端点不存在 → 创建异步任务，由 binance-service 调用币安 API
   ↓
5. 异步任务完成后，更新 klines_history 表
   ↓
6. data_processor 查询 klines_history 返回数据给前端
```

**端点验证规则**:
- **只验证起始和结束两个时间点**的K线数据
- **中间数据不验证**（缺失不影响图表显示，可由前端填充或忽略）
- 验证通过 `check_kline_endpoints_exist()` 方法实现

**设计理由**:
| 方面 | 说明 |
|------|------|
| 减少API调用 | 数据库已有近80万条4h K线数据，无需每次重复获取 |
| 端点关键性 | 起始点是图表左边界，结束点是图表右边界，必须存在 |
| 前端容忍 | TradingView 前端可以处理中间数据缺失（显示为断点或等待加载） |
| 资源节省 | 避免不必要的网络请求和API限流风险 |

**代码位置**:
- **api-service**: `src/gateway/task_router.py` - `_handle_get()` 方法
- **验证方法**: `TasksRepository.check_kline_endpoints_exist()`
- **数据仓储**: `TasksRepository.query_klines_range()`

**日志示例**:
```
# 缓存命中（端点完整）→ 直接返回
INFO - 缓存命中（端点完整）: BINANCE:BTCUSDT 240 (1763352000000 - 1771156800000)

# 缓存缺失（端点不完整）→ 创建异步任务
INFO - 缓存缺失（端点不完整）: BINANCE:BTCUSDT 240 缺少: from_time, to_time，创建异步任务
```

**⚠️ 重构注意事项**:
> 此设计是系统的核心优化点，每次重构 api-service 时必须保留：
> 1. 时间对齐逻辑必须在创建任务前执行
> 2. 必须先检查 `klines_history` 表的端点数据
> 3. 只有端点缺失时才创建异步任务
> 4. 违反此设计会导致不必要的 API 调用和性能问题

**确认响应（阶段 2）**:
```json
{
    "protocolVersion": "2.0",
    "type": "ACK",
    "requestId": "req_1703123456789_004",
    "timestamp": 1703123456790,
    "data": {}
}
```

> **说明**: data 为空对象，无需额外信息。requestId 已足够用于关联请求和响应。

**成功响应（阶段 3，包含 K 线数据）**:
```json
{
    "protocolVersion": "2.0",
    "type": "KLINES_DATA",
    "requestId": "req_1703123456789_004",
    "timestamp": 1703123456800,
    "data": {
        "symbol": "BINANCE:BTCUSDT",
        "interval": "60",
        "bars": [...],
        "count": 100,
        "noData": false
    }
}
```

---

##### 1.5 获取服务器时间

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_SERVER_TIME",
    "requestId": "req_1703123456789_005",
    "timestamp": 1703123456789,
    "data": {}
    }
}
```

**说明**:
- 对应 TradingView 的 `getServerTime` 方法
- 用于获取服务器时间

----

##### 1.6 获取期货账户信息

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_FUTURES_ACCOUNT",
    "requestId": "req_account_001",
    "timestamp": 1703123456789,
    "data": {}
}
```

**说明**:
- 需要有效的 API 密钥认证
- 返回 U 本位合约账户信息，包括余额、持仓、保证金等
- `account` 字段为 **JSON 对象**，包含 Binance API 返回的完整字段，前端可直接使用

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "ACCOUNT_DATA",
    "requestId": "req_account_001",
    "timestamp": 1703123456790,
    "data": {
        "account": {
            "feeTier": 5,
            "canTrade": true,
            "canDeposit": true,
            "canWithdraw": true,
            "totalInitialMargin": "1000.00000000",
            "totalMaintMargin": "50.00000000",
            "totalWalletBalance": "5000.00000000",
            "totalUnrealizedProfit": "100.50000000",
            "totalMarginBalance": "5100.50000000",
            "update_time": 1703123456000,
            "positions": [
                {
                    "symbol": "BTCUSDT",
                    "position_side": "LONG",
                    "position_amt": "0.500",
                    "entry_price": "45000.0",
                    "mark_price": "45200.0",
                    "unrealized_profit": "100.00000000",
                    "liquidation_price": "42000.0",
                    "margin_size": "500.00000000"
                }
            ]
        }
    }
}
```

---

##### 1.7 获取现货账户信息

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_SPOT_ACCOUNT",
    "requestId": "req_account_002",
    "timestamp": 1703123456789,
    "data": {}
}
```

**说明**:
- 需要有效的 API 密钥认证
- 返回现货账户信息，包括余额、手续费率、权限等
- `account` 字段为 **JSON 对象**，包含 Binance API 返回的完整字段，前端可直接使用

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "ACCOUNT_DATA",
    "requestId": "req_account_002",
    "timestamp": 1703123456790,
    "data": {
        "account": {
            "makerCommission": 10,
            "taker_commission": 10,
            "buyer_commission": 0,
            "seller_commission": 0,
            "can_trade": true,
            "can_withdraw": true,
            "can_deposit": true,
            "update_time": 1703123456000,
            "account_type": "SPOT",
            "balances": [
                {"asset": "USDT", "free": "1000.00", "locked": "0.00"},
                {"asset": "BTC", "free": "0.01", "locked": "0.00"}
            ],
            "permissions": ["SPOT", "MARGIN"]
        }
    }
}
```

---

##### 1.8 查询当前客户端订阅

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_SUBSCRIPTIONS",
    "requestId": "req_1703123456789_006",
    "timestamp": 1703123456789,
    "data": {}
}
```

**说明**:
- 自定义扩展API
- 用于查询当前客户端的所有活跃订阅
- 返回当前连接已订阅的所有数据流

---

##### 1.7 批量获取 Quotes 报价数据

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_QUOTES",
    "requestId": "req_1703123456789_006",
    "timestamp": 1703123456789,
    "data": {
        "symbols": ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"]
    }
}
```

**字段说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | ✅ | 固定为 `quotes` |
| `symbols` | string[] | ✅ | 交易对列表，格式：`EXCHANGE:SYMBOL` |

**说明**:
- 用于批量获取多个交易对的实时报价数据
- 数据来源：币安 24hr ticker 统计 API
- 支持多交易所混合查询
- 单次最多 50 个交易对

---

#### 2. 订阅请求 (v2.0)

**格式要求**: 使用订阅键数组格式，`data` 中包含 `subscriptions` 数组字段。**仅支持数组格式，不支持字典格式。**

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "SUBSCRIBE",
    "requestId": "req_1703123456789_007",
    "timestamp": 1703123456789,
    "data": {
        "subscriptions": [
            "BINANCE:BTCUSDT@KLINE_1",
            "BINANCE:BTCUSDT@KLINE_60",
            "BINANCE:BTCUSDT@QUOTES",
            "BINANCE:ETHUSDT@KLINE_1",
            "BINANCE:BTCUSDT.PERP@KLINE_1"
        ]
    }
}
```

**订阅键格式说明**:
- `{EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]`
- 数据类型：`KLINE`、`QUOTES`、`TRADE`（TV兼容，使用全大写格式）
- 分辨率：TV格式，如 `1`、`60`、`D` 等
- **重要**: 前端发送的订阅键格式与内部存储格式完全一致，无需大小写转换

**速率限制**:
- 每次发送一个请求包
- 每个包最多包含 **50个流**
- 请求间隔：250ms（4次/秒）
- 遵守币安WebSocket API的5 msg/s限制，留出ping包空间

**订阅类型（已实现）**:
| 订阅类型 | 订阅键示例 | 币安对应流 | TV兼容 | 更新频率 |
|---------|-----------|-----------|--------|----------|
| `KLINE` | `BINANCE:BTCUSDT@KLINE_1` | `<symbol>@kline_<interval>` | ✅ 是 | 周期更新（每秒聚合） |
| `QUOTES` | `BINANCE:BTCUSDT@QUOTES` | `<symbol>@ticker` | ✅ 是 | 实时推送 |
| `TRADE` | `BINANCE:BTCUSDT@TRADE` | `<symbol>@trade` | ✅ 是 | 实时推送 |
| `ACCOUNT` | `BINANCE:ACCOUNT@SPOT` | 用户数据流 | ❌ 否 | 实时推送（增量） |
| `ACCOUNT` | `BINANCE:ACCOUNT@FUTURES` | 用户数据流 | ❌ 否 | 实时推送（增量） |

> **注意**：ACCOUNT 订阅是增量数据推送，前端需要先通过 GET 请求获取完整数据，再订阅增量更新。

> **重要**: TV中称为"QUOTES"而非"TICKER"，系统内部将TICKER转换为QUOTES以保持TV兼容性。

---

#### 3. 取消订阅请求 (v2.0)

**精确取消**:
```json
{
    "protocolVersion": "2.0",
    "type": "UNSUBSCRIBE",
    "requestId": "req_1703123456789_008",
    "timestamp": 1703123456789,
    "data": {
        "subscriptions": [
            "BINANCE:BTCUSDT@KLINE_60",
            "BINANCE:BTCUSDT@QUOTES"
        ]
    }
}
```

**全部取消**:
```json
{
    "protocolVersion": "2.0",
    "type": "UNSUBSCRIBE",
    "requestId": "req_1703123456789_009",
    "timestamp": 1703123456789,
    "data": {
        "all": true
    }
}
```

---

### 服务端响应

#### 1. GET 请求响应

> **重要**：所有 GET 请求都遵循三阶段模式：收到请求 → **ACK 确认** → 处理 → **数据类型响应**

所有 GET 请求的最终响应都使用具体的数据类型（如 `KLINES_DATA`、`CONFIG_DATA` 等），通过数据类型区分具体操作。**注意：数据类型是最终响应，而非第一阶段确认消息。**

##### 1.1 数据源配置响应

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "CONFIG_DATA",
    "requestId": "req_1703123456789_001",
    "timestamp": 1703123456790,
    "data": {
        "supports_search": true,
        "supports_group_request": false,
        "supports_marks": false,
        "supports_timescale_marks": false,
        "supports_time": true,
        "supported_resolutions": ["1", "5", "15", "60", "240", "1D", "1W", "1M"],
        "currency_codes": ["USDT", "BTC", "ETH", "BNB", "BUSD", "USDC", "FDUSD"],
        "symbols_types": [
            { "name": "All types", "value": "" },
            { "name": "Crypto", "value": "crypto" }
        ]
    }
}
```

---

##### 1.2 交易对搜索响应

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "SEARCH_SYMBOLS_DATA",
    "requestId": "req_1703123456789_002",
    "timestamp": 1703123456790,
    "data": {
        "symbols": [
            {
                "symbol": "BINANCE:BTCUSDT",
                "fullName": "BINANCE:BTCUSDT",
                "description": "BTC/USDT",
                "exchange": "BINANCE",
                "ticker": "BTCUSDT",
                "type": "crypto"
            },
            {
                "symbol": "BINANCE:ETHUSDT",
                "fullName": "BINANCE:ETHUSDT",
                "description": "ETH/USDT",
                "exchange": "BINANCE",
                "ticker": "ETHUSDT",
                "type": "crypto"
            }
        ],
        "total": 2,
        "count": 2
    }
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 标的全名（格式：EXCHANGE:SYMBOL） |
| `full_name` | string | 标的全名（与 symbol 相同） |
| `description` | string | 标的描述 |
| `exchange` | string | 交易所 |
| `ticker` | string | 交易代码 |
| `type` | string | 标的类型 |

---

##### 1.3 交易对详情响应

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "CONFIG_DATA",
    "requestId": "req_1703123456789_003",
    "timestamp": 1703123456790,
    "data": {
        "type": "resolve_symbol",
        "name": "BTCUSDT",
        "ticker": "BINANCE:BTCUSDT",
        "description": "BTC/USDT",
        "type": "crypto",
        "exchange": "BINANCE",
        "listed_exchange": "BINANCE",
        "currency_code": "USDT",
        "session": "24x7",
        "timezone": "Etc/UTC",
        "format": "price",
        "minmov": 1.0,
        "pricescale": 100,
        "has_intraday": true,
        "has_daily": true,
        "has_weekly_and_monthly": true,
        "visible_plots_set": "ohlcv",
        "data_status": "streaming",
        "supported_resolutions": ["1", "5", "15", "60", "240", "1D", "1W", "1M"],
        "intraday_multipliers": ["1", "5", "15", "60"],
        "daily_multipliers": ["1"],
        "weekly_multipliers": ["1"],
        "monthly_multipliers": ["1"],
        "volume_precision": 8,
        "delay": 0,
        "session_holidays": ""
    }
}
```

---

##### 1.4 K 线数据响应

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "CONFIG_DATA",
    "requestId": "req_1703123456789_004",
    "timestamp": 1703123456790,
    "data": {
        "type": "klines",
        "symbol": "BINANCE:BTCUSDT",
        "interval": "60",
        "bars": [
            {
                "time": 1703123456000,
                "open": 42000.50,
                "high": 42100.00,
                "low": 41950.00,
                "close": 42080.00,
                "volume": 125.4321
            }
        ],
        "count": 1,
        "no_data": false
    }
}
```

**Bar 数据结构**:
```json
{
    "time": 1703123456000,      // bar时间（Unix时间戳，毫秒，UTC）
    "open": 42000.50,           // 开盘价
    "high": 42100.00,            // 最高价
    "low": 41950.00,            // 最低价
    "close": 42080.00,          // 收盘价
    "volume": 125.4321           // 交易量（可选）
}
```

---

##### 1.5 服务器时间响应

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "CONFIG_DATA",
    "requestId": "req_1703123456789_005",
    "timestamp": 1703123456790,
    "data": {
        "type": "server_time",
        "server_time": 1703123456789,
        "timezone": "UTC"
    }
}
```

---

##### 1.6 查询当前客户端订阅响应

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "CONFIG_DATA",
    "requestId": "req_1703123456789_006",
    "timestamp": 1703123456790,
    "data": {
        "type": "subscriptions",
        "subscriptions": [
            {
                "subscriptionKey": "BINANCE:BTCUSDT@KLINE_1",
                "dataType": "kline",
                "exchange": "BINANCE",
                "symbol": "BTCUSDT",
                "interval": "1",
                "productType": "spot",
                "status": "active",
                "subscribedAt": 1703123456000,
                "messageCount": 156,
                "lastMessageAt": 1703123456790
            },
            {
                "subscriptionKey": "BINANCE:BTCUSDT@QUOTES",
                "dataType": "quotes",
                "exchange": "BINANCE",
                "symbol": "BTCUSDT",
                "productType": "spot",
                "status": "active",
                "subscribedAt": 1703123456500,
                "messageCount": 89,
                "lastMessageAt": 1703123456785
            },
            {
                "subscriptionKey": "BINANCE:ETHUSDT@KLINE_60",
                "dataType": "kline",
                "exchange": "BINANCE",
                "symbol": "ETHUSDT",
                "interval": "60",
                "productType": "spot",
                "status": "active",
                "subscribedAt": 1703123457000,
                "messageCount": 23,
                "lastMessageAt": 1703123456770
            }
        ],
        "total": 3,
        "activeCount": 3,
        "inactiveCount": 0
    }
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| `subscriptions` | array | 订阅列表 |
| `subscriptions[].subscriptionKey` | string | 订阅键（v2.0格式） |
| `subscriptions[].dataType` | string | 数据类型（kline/quotes/trade） |
| `subscriptions[].exchange` | string | 交易所代码 |
| `subscriptions[].symbol` | string | 交易对代码 |
| `subscriptions[].interval` | string | 分辨率（如适用） |
| `subscriptions[].productType` | string | 产品类型（spot/perpetual/quarterly） |
| `subscriptions[].status` | string | 订阅状态（active/inactive/error） |
| `subscriptions[].subscribedAt` | number | 订阅时间戳 |
| `subscriptions[].messageCount` | number | 接收到的消息数量 |
| `subscriptions[].lastMessageAt` | number | 最后一条消息时间戳 |
| `total` | number | 总订阅数 |
| `activeCount` | number | 活跃订阅数 |
| `inactiveCount` | number | 非活跃订阅数 |

**说明**:
- 返回当前客户端的所有订阅信息
- 包括订阅键、状态、统计信息等
- 用于前端自助查询和管理订阅

**空订阅响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "CONFIG_DATA",
    "requestId": "req_1703123456789_006",
    "timestamp": 1703123456790,
    "data": {
        "type": "subscriptions",
        "subscriptions": [],
        "total": 0,
        "activeCount": 0,
        "inactiveCount": 0
    }
}
```

---

##### 1.7 Quotes 报价数据响应

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "CONFIG_DATA",
    "requestId": "req_1703123456789_006",
    "timestamp": 1703123456790,
    "data": {
        "type": "quotes",
        "quotes": [
            {
                "n": "BINANCE:BTCUSDT",
                "s": "ok",
                "v": {
                    "ch": 123.45,
                    "chp": 2.35,
                    "short_name": "BTCUSDT",
                    "exchange": "BINANCE",
                    "description": "比特币/泰达币",
                    "lp": 50000.00,
                    "ask": 50001.00,
                    "bid": 49999.00,
                    "spread": 2.00,
                    "open_price": 49000.00,
                    "high_price": 50500.00,
                    "low_price": 48800.00,
                    "prev_close_price": 49876.55,
                    "volume": 1234.56
                }
            },
            {
                "n": "BINANCE:ETHUSDT",
                "s": "ok",
                "v": {
                    "ch": -50.25,
                    "chp": -1.35,
                    "lp": 3680.50,
                    "ask": 3681.00,
                    "bid": 3680.00,
                    "spread": 1.00,
                    "open_price": 3635.30,
                    "high_price": 3720.00,
                    "low_price": 3610.00,
                    "prev_close_price": 3730.75,
                    "volume": 234567.80
                }
            }
        ]
    }
}
```

**Quotes 数据字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| `n` | string | 标的全名（EXCHANGE:SYMBOL） |
| `s` | string | 状态（ok/error） |
| `v.ch` | number | 价格变化 |
| `v.chp` | number | 价格变化百分比 |
| `v.short_name` | string | 短名称（如 BTCUSDT） |
| `v.exchange` | string | 交易所名称（如 BINANCE） |
| `v.description` | string | 标的描述（如 比特币/泰达币） |
| `v.lp` | number | 最新价格（last price） |
| `v.ask` | number | 卖价 |
| `v.bid` | number | 买价 |
| `v.spread` | number | 价差 |
| `v.open_price` | number | 开盘价 |
| `v.high_price` | number | 最高价 |
| `v.low_price` | number | 最低价 |
| `v.prev_close_price` | number | 前收盘价 |
| `v.volume` | number | 成交量 |

**数据来源**:
- 币安 24hr ticker 统计 API：`/api/v3/ticker/24hr`
- 数据转换：将币安 ticker 字段映射为 TradingView quotes 格式

---

##### 1.8 告警配置管理

告警配置系统用于创建和管理交易策略告警，支持 MACD 共振等信号策略的实时监控。

###### 1.8.1 创建告警配置

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "CREATE_ALERT_CONFIG",
    "requestId": "req_alert_001",
    "timestamp": 1704067200000,
    "data": {
        "name": "macd_resonance_btcusdt",
        "description": "BTCUSDT MACD共振告警",
        "strategyType": "MACDResonanceStrategyV5",
        "symbol": "BINANCE:BTCUSDT",
        "interval": "60",
        "triggerType": "each_kline_close",
        "params": {
            "macd1Fastperiod": 12,
            "macd1Slowperiod": 26,
            "macd1Signalperiod": 9,
            "macd2Fastperiod": 4,
            "macd2Slowperiod": 20,
            "macd2Signalperiod": 4
        },
        "isEnabled": true,
        "createdBy": "user_001"
    }
}
```

**字段说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 告警名称 |
| `description` | string | ❌ | 告警描述 |
| `strategyType` | string | ✅ | 策略类型（如 `MACDResonanceStrategyV5`、`MACDResonanceStrategyV6`、`MACDResonanceShortStrategy`、`Alpha01Strategy`） |
| `symbol` | string | ✅ | 交易对（格式：`EXCHANGE:SYMBOL`） |
| `interval` | string | ✅ | K线周期（如 `1`, `60`, `1D`） |
| `triggerType` | string | ✅ | 触发类型（`once_only`, `each_kline`, `each_kline_close`, `each_minute`） |
| `params` | object | ✅ | 策略参数（JSON对象） |
| `isEnabled` | boolean | ✅ | 是否启用 |
| `createdBy` | string | ✅ | 创建者标识 |

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "ALERT_CONFIG_DATA",
    "requestId": "req_alert_001",
    "timestamp": 1704067201000,
    "data": {
        "type": "create_alert_config",
        "id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
        "name": "macd_resonance_btcusdt",
        "description": "BTCUSDT MACD共振告警",
        "strategy_type": "MACDResonanceStrategyV5",
        "symbol": "BINANCE:BTCUSDT",
        "interval": "60",
        "trigger_type": "each_kline_close",
        "params": {
            "macd1_fastperiod": 12,
            "macd1_slowperiod": 26,
            "macd1_signalperiod": 9,
            "macd2_fastperiod": 4,
            "macd2_slowperiod": 20,
            "macd2_signalperiod": 4
        },
        "is_enabled": true,
        "created_at": "2026-02-13T10:00:00Z",
        "created_by": "user_001"
    }
}
```

---

###### 1.8.2 列出告警配置

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "LIST_ALERT_CONFIGS",
    "requestId": "req_list_001",
    "timestamp": 1704067200000,
    "data": {
        "page": 1,
        "pageSize": 20,
        "strategyType": "MACDResonanceStrategyV5",
        "symbol": "BINANCE:BTCUSDT"
    }
}
```

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "ALERT_CONFIG_DATA",
    "requestId": "req_list_001",
    "timestamp": 1704067201000,
    "data": {
        "items": [
            {
                "id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
                "name": "macd_resonance_btcusdt",
                "description": "BTCUSDT MACD共振告警",
                "strategyType": "MACDResonanceStrategyV5",
                "symbol": "BINANCE:BTCUSDT",
                "interval": "60",
                "triggerType": "each_kline_close",
                "params": {
                    "macd1Fastperiod": 12,
                    "macd1Slowperiod": 26,
                    "macd1_signalperiod": 9,
                    "macd2_fastperiod": 5,
                    "macd2_slowperiod": 35,
                    "macd2_signalperiod": 5
                },
                "is_enabled": true,
                "created_at": "2026-02-13T10:00:00Z",
                "created_by": "user_001"
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20
    }
}
```

---

###### 1.8.3 查询历史信号

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "LIST_SIGNALS",
    "requestId": "req_signals_001",
    "timestamp": 1704067200000,
    "data": {
        "page": 1,
        "pageSize": 20,
        "symbol": "BINANCE:BTCUSDT",
        "strategyType": "MACDResonanceStrategyV5",
        "fromTime": 1703980800000,
        "toTime": 1704067200000
    }
}
```

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "SIGNAL_DATA",
    "requestId": "req_signals_001",
    "timestamp": 1704067201000,
    "data": {
        "items": [
            {
                "id": 1,
                "signalId": "0189a1b3-c4d5-6e7f-8901-bcde23456789",
                "alertId": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
                "createdBy": "user_001",
                "strategyType": "MACDResonanceStrategyV5",
                "symbol": "BINANCE:BTCUSDT",
                "interval": "60",
                "signalValue": true,
                "computedAt": "2026-02-13T10:00:00Z"
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20
    }
}
```

**信号值说明**:
| 值 | 说明 |
|---|------|
| `true` | 做多信号 |
| `false` | 做空信号 |
| `null` | 无信号/观望 |

---

###### 1.8.4 更新告警配置

**请求字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | ✅ | 固定为 `update_alert_config` |
| id | string | ✅ | 告警配置 ID |
| name | string | - | 告警名称 |
| description | string | - | 告警描述 |
| strategy_type | string | - | 策略类型（如 MACDResonanceStrategyV5） |
| symbol | string | - | 交易对（如 BINANCE:BTCUSDT） |
| interval | string | - | K线周期（如 60） |
| trigger_type | string | - | 触发类型 |
| params | object | - | 策略参数 |
| is_enabled | boolean | - | 是否启用 |

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "UPDATE_ALERT_CONFIG",
    "requestId": "req_update_001",
    "timestamp": 1704067200000,
    "data": {
        "id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
        "name": "macd_resonance_btcusdt_updated",
        "strategyType": "MACDResonanceStrategyV5",
        "params": {
            "fast1": 8,
            "macd1Slowperiod": 21,
            "macd1Signalperiod": 5,
            "macd2Fastperiod": 3,
            "macd2Slowperiod": 15,
            "macd2Signalperiod": 3
        }
    }
}
```

**成功响应**：
```json
{
    "protocolVersion": "2.0",
    "type": "ALERT_CONFIG_DATA",
    "requestId": "req_update_001",
    "timestamp": 1704067201000,
    "data": {
        "id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
        "name": "macd_resonance_btcusdt_updated",
        "description": "更新后的描述",
        "strategyType": "MACDResonanceStrategyV5",
        "symbol": "BINANCE:BTCUSDT",
        "interval": "60",
        "trigger_type": "each_kline_close",
        "params": {
            "fast1": 8,
            "macd1_slowperiod": 21,
            "macd1_signalperiod": 5,
            "macd2_fastperiod": 3,
            "macd2_slowperiod": 15,
            "macd2_signalperiod": 3
        },
        "is_enabled": true,
        "created_at": "2026-02-13T10:00:00Z",
        "updated_at": "2026-02-13T11:00:00Z",
        "created_by": "user_001"
    }
}
```

**重要说明**：
- 更新响应返回完整的告警配置数据，前端需要使用此数据更新本地状态
- 与 `create_alert_config` 响应格式保持一致，确保前端统一处理

---

###### 1.8.5 删除告警配置

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "DELETE_ALERT_CONFIG",
    "requestId": "req_delete_001",
    "timestamp": 1704067200000,
    "data": {
        "id": "0189a1b2-c3d4-5e6f-7890-abcd12345678"
    }
}
```

---

###### 1.8.6 启用/禁用告警配置

**启用请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "ENABLE_ALERT_CONFIG",
    "requestId": "req_enable_001",
    "timestamp": 1704067200000,
    "data": {
        "id": "0189a1b2-c3d4-5e6f-7890-abcd12345678"
    }
}
```

---

##### 1.9 策略元数据管理

策略元数据API用于获取系统已注册的策略列表及其参数定义。前端在创建/编辑告警时，需要先调用 `GET_STRATEGY_METADATA` 获取策略列表，然后根据用户选择的策略类型的 `type` 字段（策略类名）作为 `strategyType` 值发送请求。

**重要**：
- `type` 字段的值为策略**类名**（如 `MACDResonanceStrategyV5`），前端必须使用此值作为创建/更新告警时的 `strategy_type` 字段
- 前端**禁止**自行转换或映射策略类型，必须直接使用后端返回的 `type` 值
- 可用策略类型：`MACDResonanceStrategyV5`、`MACDResonanceStrategyV6`、`MACDResonanceShortStrategy`、`Alpha01Strategy`、`RandomStrategy`

###### 1.9.1 获取所有策略元数据

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_STRATEGY_METADATA",
    "requestId": "req_strategy_001",
    "timestamp": 1704067200000,
    "data": {}
}
```

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "STRATEGY_METADATA_DATA",
    "requestId": "req_strategy_001",
    "timestamp": 1704067201000,
    "data": {
        "strategies": [
            {
                "type": "MACDResonanceStrategyV5",
                "name": "MACD共振策略V5",
                "description": "双MACD指标金叉/死叉共振，结合EMA均线系统过滤，捕捉趋势交易机会",
                "params": [
                    {
                        "name": "macd1Fastperiod",
                        "type": "int",
                        "default": 12,
                        "min": 1,
                        "max": 100,
                        "description": "MACD1快速EMA周期"
                    },
                    {
                        "name": "macd1_slowperiod",
                        "type": "int",
                        "default": 26,
                        "min": 1,
                        "max": 200,
                        "description": "MACD1慢速EMA周期"
                    },
                    {
                        "name": "macd1_signalperiod",
                        "type": "int",
                        "default": 9,
                        "min": 1,
                        "max": 50,
                        "description": "MACD1信号线周期"
                    },
                    {
                        "name": "macd2_fastperiod",
                        "type": "int",
                        "default": 4,
                        "min": 1,
                        "max": 50,
                        "description": "MACD2快速EMA周期"
                    },
                    {
                        "name": "macd2_slowperiod",
                        "type": "int",
                        "default": 20,
                        "min": 1,
                        "max": 100,
                        "description": "MACD2慢速EMA周期"
                    },
                    {
                        "name": "macd2_signalperiod",
                        "type": "int",
                        "default": 4,
                        "min": 1,
                        "max": 50,
                        "description": "MACD2信号线周期"
                    }
                ]
            },
            {
                "type": "MACDResonanceStrategyV6",
                "name": "MACD共振策略V6",
                "description": "MACD共振策略V6性能优化版，使用numpy数组替代pandas Series进行计算，大幅提升性能",
                "params": [
                    {
                        "name": "macd1_fastperiod",
                        "type": "int",
                        "default": 12,
                        "min": 1,
                        "max": 100,
                        "description": "MACD1快速EMA周期"
                    },
                    {
                        "name": "macd1_slowperiod",
                        "type": "int",
                        "default": 26,
                        "min": 1,
                        "max": 200,
                        "description": "MACD1慢速EMA周期"
                    },
                    {
                        "name": "macd1_signalperiod",
                        "type": "int",
                        "default": 9,
                        "min": 1,
                        "max": 50,
                        "description": "MACD1信号线周期"
                    },
                    {
                        "name": "macd2_fastperiod",
                        "type": "int",
                        "default": 4,
                        "min": 1,
                        "max": 50,
                        "description": "MACD2快速EMA周期"
                    },
                    {
                        "name": "macd2_slowperiod",
                        "type": "int",
                        "default": 20,
                        "min": 1,
                        "max": 100,
                        "description": "MACD2慢速EMA周期"
                    },
                    {
                        "name": "macd2_signalperiod",
                        "type": "int",
                        "default": 4,
                        "min": 1,
                        "max": 50,
                        "description": "MACD2信号线周期"
                    }
                ]
            },
            {
                "type": "MACDResonanceShortStrategy",
                "name": "MACD做空策略",
                "description": "基于双MACD共振的基本做空策略，通过死叉信号捕捉下跌趋势中的做空机会",
                "params": [
                    {
                        "name": "macd1_fastperiod",
                        "type": "int",
                        "default": 12,
                        "min": 1,
                        "max": 100,
                        "description": "MACD1快速EMA周期"
                    },
                    {
                        "name": "macd1_slowperiod",
                        "type": "int",
                        "default": 26,
                        "min": 1,
                        "max": 200,
                        "description": "MACD1慢速EMA周期"
                    },
                    {
                        "name": "macd1_signalperiod",
                        "type": "int",
                        "default": 9,
                        "min": 1,
                        "max": 50,
                        "description": "MACD1信号线周期"
                    },
                    {
                        "name": "macd2_fastperiod",
                        "type": "int",
                        "default": 4,
                        "min": 1,
                        "max": 50,
                        "description": "MACD2快速EMA周期"
                    },
                    {
                        "name": "macd2_slowperiod",
                        "type": "int",
                        "default": 20,
                        "min": 1,
                        "max": 100,
                        "description": "MACD2慢速EMA周期"
                    },
                    {
                        "name": "macd2_signalperiod",
                        "type": "int",
                        "default": 4,
                        "min": 1,
                        "max": 50,
                        "description": "MACD2信号线周期"
                    }
                ]
            },
            {
                "type": "Alpha01Strategy",
                "name": "Alpha01策略",
                "description": "基于ATR止损和枢轴点的趋势跟踪策略",
                "params": [
                    {
                        "name": "ema_period",
                        "type": "int",
                        "default": 50,
                        "min": 1,
                        "max": 500,
                        "description": "EMA周期"
                    },
                    {
                        "name": "volume_ma_period",
                        "type": "int",
                        "default": 20,
                        "min": 1,
                        "max": 200,
                        "description": "成交量MA周期"
                    },
                    {
                        "name": "threshold",
                        "type": "float",
                        "default": 0.02,
                        "min": 0.0,
                        "max": 1.0,
                        "description": "阈值"
                    }
                ]
            }
        ]
    }
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| `strategies` | array | 策略元数据数组 |
| `strategies[].type` | string | 策略类型标识符 |
| `strategies[].name` | string | 策略显示名称 |
| `strategies[].description` | string | 策略描述 |
| `strategies[].params` | array | 策略参数数组 |
| `params[].name` | string | 参数名称 |
| `params[].type` | string | 参数类型（int, float, bool） |
| `params[].default` | number/boolean | 默认值 |
| `params[].min` | number | 最小值 |
| `params[].max` | number | 最大值 |
| `params[].description` | string | 参数描述 |

**使用场景**:
1. 前端加载告警配置表单时，先调用此接口获取策略列表
2. 用户选择策略后，前端根据 `params` 数组动态渲染参数输入控件
3. 参数类型决定使用哪种输入组件（int/float 用数字输入框，bool 用开关）

---

###### 1.9.2 获取指定策略元数据

**示例请求**:
```json
{
    "protocolVersion": "2.0",
    "type": "GET_STRATEGY_METADATA_BY_TYPE",
    "requestId": "req_strategy_002",
    "timestamp": 1704067200000,
    "data": {
        "strategyType": "MACDResonanceStrategyV5"
    }
}
```

**成功响应**:
```json
{
    "protocolVersion": "2.0",
    "type": "STRATEGY_METADATA_DATA",
    "requestId": "req_strategy_002",
    "timestamp": 1704067201000,
    "data": {
        "strategy": {
            "type": "MACDResonanceStrategyV5",
            "name": "MACD共振策略V5",
            "description": "双MACD指标金叉/死叉共振，结合EMA均线系统过滤，捕捉趋势交易机会",
            "params": [
                {
                    "name": "macd1Fastperiod",
                    "type": "int",
                    "default": 12,
                    "min": 1,
                    "max": 100,
                    "description": "MACD1快速EMA周期"
                }
            ]
        }
    }
}
```

---

#### 2. 订阅确认响应 (v2.0)

> **重要**：订阅请求遵循三阶段模式：收到请求 → **ack 确认** → 处理 → **success 响应**
>
> **注意**：`success` 响应**不是实时数据**，实时数据通过独立的 `update` 推送消息传递。

**响应格式**:
```json
// 阶段1: ACK 确认
{
    "protocolVersion": "2.0",
    "type": "ACK",
    "requestId": "req_1703123456789_007",
    "timestamp": 1703123456790,
    "data": {}
}

// 阶段2: 数据类型响应
{
    "protocolVersion": "2.0",
    "type": "SUBSCRIPTION_DATA",
    "requestId": "req_1703123456789_007",
    "timestamp": 1703123456790,
    "data": {
        "subscriptions": [...]
    }
}
```

**三阶段说明**：

| 阶段 | type | 是否有 requestId | 说明 |
|------|------|------------------|------|
| 1 | `ACK` | ✅ 有 | 确认收到订阅请求，返回空 data 对象 |
| 2 | `SUBSCRIPTION_DATA` | ✅ 有 | 确认订阅处理完成，返回订阅列表 |
| - | `UPDATE` | ❌ 无 | **实时数据推送**（独立机制，不属于请求-响应流程） |

**重要区分**：
- `success` 响应：请求-响应模式的最终回复，包含 `requestId`
- `update` 推送：服务端主动推送的实时数据，**不包含 requestId**，遵循 TradingView 规范
- 订阅是否成功通过后续的 `update` 推送消息来验证

---

#### 3. 取消订阅确认响应 (v2.0)

> **重要**：取消订阅请求遵循三阶段模式：收到请求 → **ack 确认** → 处理 → **success 响应**

**响应格式**:
```json
// 阶段1: ACK 确认
{
    "protocolVersion": "2.0",
    "type": "ACK",
    "requestId": "req_1703123456789_008",
    "timestamp": 1703123456790,
    "data": {}
}

// 阶段2: 数据类型响应
{
    "protocolVersion": "2.0",
    "type": "SUBSCRIPTION_DATA",
    "requestId": "req_1703123456789_008",
    "timestamp": 1703123456790,
    "data": {}
}
```

**三阶段说明**：

| 阶段 | type | 是否有 requestId | 说明 |
|------|------|------------------|------|
| 1 | `ACK` | ✅ 有 | 确认收到取消订阅请求，返回空 data 对象 |
| 2 | `SUBSCRIPTION_DATA` | ✅ 有 | 确认取消订阅处理完成 |

**重要区分**：
- `success` 响应：请求-响应模式的最终回复，包含 `requestId`
- 取消订阅不涉及实时数据推送，因此无 `update` 消息

---

### 实时数据推送 (v2.0)

> **重要说明**：`update` 推送是**独立于请求-响应流程**的实时数据推送机制。
>
> - `success` 响应：属于请求-响应模式，有 `request `update` Id`
> -推送：**不属于请求-响应流程**，**无 requestId**，是服务端主动推送

#### 命名规范

**命名区分**：
- `content`: 实时推送的实际数据内容（避免与数据库 `payload` 混淆）
- `payload`: 数据库任务表（tasks）的载荷字段

#### 逐个推送格式

**K线数据推送**:
```json
{
    "protocolVersion": "2.0",
    "type": "UPDATE",
    "timestamp": 1703123456790,
    "data": {
        "subscriptionKey": "BINANCE:BTCUSDT@KLINE_1",
        "bar": {
            "time": 1703123400000,
            "open": 97000.00,
            "high": 97600.00,
            "low": 96800.00,
            "close": 97500.00,
            "volume": 125.43
        }
    }
}
```

**QUOTES数据推送**:
```json
{
    "protocolVersion": "2.0",
    "type": "UPDATE",
    "timestamp": 1703123456790,
    "data": {
        "subscriptionKey": "BINANCE:BTCUSDT@QUOTES",
        "quote": {
            "n": "BINANCE:BTCUSDT",
            "s": "ok",
            "v": {
                "ch": 123.45,
                "chp": 2.35,
                "short_name": "BTCUSDT",
                "exchange": "BINANCE",
                "description": "比特币/泰达币",
                "lp": 97500.00,
                "ask": 97501.00,
                "bid": 97499.00,
                "spread": 2.00,
                "open_price": 96249.50,
                "high_price": 98000.00,
                "low_price": 95800.00,
                "prev_close_price": 97376.55,
                "volume": 45678.90
            }
        }
    }
}
```

**QUOTES数据批量推送**:
```json
{
    "protocolVersion": "2.0",
    "type": "UPDATE",
    "timestamp": 1703123456790,
    "data": {
        "subscriptionKey": "BINANCE:BTCUSDT@QUOTES,BINANCE:ETHUSDT@QUOTES",
        "quotes": [
            {
                "n": "BINANCE:BTCUSDT",
                "s": "ok",
                "v": {
                    "ch": 123.45,
                    "chp": 2.35,
                    "short_name": "BTCUSDT",
                    "exchange": "BINANCE",
                    "description": "比特币/泰达币",
                    "lp": 97500.00,
                    "ask": 97501.00,
                    "bid": 97499.00,
                    "spread": 2.00,
                    "open_price": 96249.50,
                    "high_price": 98000.00,
                    "low_price": 95800.00,
                    "prev_close_price": 97376.55,
                    "volume": 45678.90
                }
            },
            {
                "n": "BINANCE:ETHUSDT",
                "s": "ok",
                "v": {
                    "ch": 5.67,
                    "chp": 1.23,
                    "short_name": "ETHUSDT",
                    "exchange": "BINANCE",
                    "description": "以太坊/泰达币",
                    "lp": 2300.00,
                    "ask": 2301.00,
                    "bid": 2299.00,
                    "spread": 2.00,
                    "open_price": 2275.50,
                    "high_price": 2310.00,
                    "low_price": 2265.00,
                    "prev_close_price": 2294.33,
                    "volume": 98765.43
                }
            }
        ]
    }
}
```

**TRADE数据推送**:
```json
{
    "protocolVersion": "2.0",
    "type": "UPDATE",
    "timestamp": 1703123456790,
    "data": {
        "subscriptionKey": "BINANCE:BTCUSDT@TRADE",
        "trade": {
            "price": 97500.00,
            "size": 0.123,
            "time": 1703123456790,
            "side": "buy"
        }
    }
}
```

#### 字段说明

**通用字段**:
- `subscriptionKey`: 订阅键，用于标识数据类型和交易对
- `bar`: K线数据内容
- `quote`: 报价数据内容
- `trade`: 交易数据内容

**K线数据字段** (TradingView Bar格式):
- `time`: 时间戳（毫秒）
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量（可选）
- `isBarClosed`: 是否为完成的K线

**QUOTES数据字段** (TradingView Quotes格式):
- `n`: 标的全名（如 BINANCE:BTCUSDT）
- `s`: 状态（ok/error）
- `v`: 报价值对象，包含以下字段：
  - `ch`: 价格变化
  - `chp`: 价格变化百分比
  - `lp`: 最新价格
  - `ask`: 卖价
  - `bid`: 买价
  - `spread`: 价差
  - `open_price`: 开盘价
  - `high_price`: 最高价
  - `low_price`: 最低价
  - `prev_close_price`: 前收盘价
  - `volume`: 成交量
  - `short_name`: 短名称
  - `exchange`: 交易所名称
  - `description`: 标的描述

#### v2.0 核心改进

1. **去除冗余字段**: 不再包含 `symbol` 和 `interval` 字段，因为订阅键已包含这些信息
2. **直接兼容**: payload直接使用TradingView期望的格式，无需额外转换
3. **逐个推送**: 每条数据独立推送，便于前端处理
4. **简化结构**: 减少嵌套层级，提高可读性

**重要说明**:
- 更新消息中**不包含** `requestId` 字段
- 这是服务器主动推送的数据，没有对应的请求
- 遵循 TradingView API 官方规范

**推送策略**:
| 数据类型 | 推送方式 | 说明 |
|---------|---------|------|
| `kline` | 批量推送 | 周期性聚合（每秒） |
| `quotes` | 批量推送 | 24hr ticker 轮询更新（每秒） |
| `SIGNAL:{alert_id}` | 实时推送 | 指定告警配置实时推送（前端订阅） |

**信号数据推送**:
当策略计算产生信号时，推送 `signal_new` 消息。**设计原则**：订阅键 `SIGNAL:{alert_id}` 已表明数据类型，`content` 直接展开业务数据，无需冗余的 `type` 字段：

```json
{
    "protocolVersion": "2.0",
    "type": "UPDATE",
    "timestamp": 1704067205000,
    "data": {
        "subscriptionKey": "SIGNAL:0189a1b2-c3d4-5e6f-7890-abcd12345678",
        "signal": {
            "alertId": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
            "name": "macd_resonance_btcusdt",
            "strategyType": "MACDResonanceStrategyV5",
            "symbol": "BINANCE:BTCUSDT",
            "interval": "60",
            "signalValue": true,
            "computedAt": "2026-02-13T10:00:05Z"
        }
    }
}
```

**设计说明**:
- `subscriptionKey: SIGNAL:xxx` 表明这是信号数据
- `signal` 直接展开业务字段，与 KLINE 数据推送格式一致
- 前端通过 `subscriptionKey.startsWith('SIGNAL:')` 识别信号推送

**订阅信号通道**:
```json
{
    "protocolVersion": "2.0",
    "type": "SUBSCRIBE",
    "requestId": "req_sub_001",
    "timestamp": 1704067200000,
    "data": {
        "subscriptions": [
            "SIGNAL:0189a1b2-c3d4-5e6f-7890-abcd12345678"
        ]
    }
}
```

**说明**：
- 前端创建告警时生成 UUIDv4 `alert_id`
- 订阅键格式为 `SIGNAL:{alert_id}`
- 前端需要手动订阅才能接收信号推送
- 前端重连后需要重新订阅

---

## 错误处理

```json
{
    "protocolVersion": "2.0",
    "type": "ERROR",
    "requestId": "req_1703123456789_004",
    "timestamp": 1703123456790,
    "data": {
        "errorCode": "INVALID_SYMBOL",
        "errorMessage": "Symbol BINANCE:INVALID not found"
    }
}
```

### 错误码定义

| 错误码 | 说明 | 示例 |
|--------|------|------|
| `INVALID_SYMBOL` | 交易对不存在或不支持 | `symbol=BINANCE:INVALID` |
| `INVALID_INTERVAL` | 分辨率不支持 | `resolution=999` |
| `INVALID_DATE_RANGE` | 无效的日期范围 | `from_time >= to_time` |
| `EXCHANGE_NOT_FOUND` | 交易所不存在 | `INVALID:BTCUSDT` |
| `RATE_LIMIT_EXCEEDED` | 请求频率超限 | 多次快速请求 |
| `INTERNAL_ERROR` | 服务器内部错误 | 未知错误 |
| `SERVICE_UNAVAILABLE` | 服务暂时不可用 | 维护期间 |
| `INVALID_SYMBOLS` | 无效的交易对列表 | symbols 参数格式错误 |
| `SYMBOL_NOT_FOUND` | 交易对不存在 | BINANCE:INVALID |
| `EXCHANGE_NOT_SUPPORTED` | 交易所不支持 | UNKNOWN:BTCUSDT |
| `SUBSCRIPTION_NOT_FOUND` | 订阅不存在 | `subscriberId=not_found` |
| `TIMEOUT` | 请求超时 | 订阅超时 |
| `UNKNOWN_ACTION` | 未知动作类型 | `action=invalid_action` |
| `INVALID_PARAMETERS` | 参数错误 | 缺少必要参数 |

---

> **数据模型说明**：详细的数据模型定义请参考 [08-api-models.md](./08-api-models.md)，该文档记录了所有代码中的 Pydantic 模型定义。

## 📝 总结

本设计方案采用**纯 WebSocket 架构**，为 TradingView 图表库提供完整的数据服务。主要特点包括：

### 1. **统一管理器架构**
   - UnifiedWebSocketManager 统一管理所有连接和订阅
   - 智能订阅计算，自动去重和优化
   - 实时连接状态和订阅跟踪
   - 提供完整的监控指标

### 2. **双客户端架构**
   - API 客户端处理非实时数据请求
   - Streams 客户端处理实时数据流
   - 职责分离，连接优化

### 3. **统一消息协议**
   - 所有交互都通过单一 WebSocket 连接
   - 统一的 JSON 消息格式
   - 支持所有 TradingView 方法

### 4. **智能订阅管理**
   - 引用计数机制，避免重复订阅
   - 支持多客户端共享数据流
   - 自动清理无用的订阅
   - 统一订阅键格式（v2.0）- 全大写格式，大小写一致性

### 5. **已实现的实时数据**
   - K 线数据订阅和推送
   - Quotes 报价订阅和推送（基于 24hr ticker 轮询）

### 6. **多交易所支持**
   - 通过统一消息格式支持不同交易所
   - 轻松扩展新交易所
   - 统一错误处理和响应格式

---

## 🔗 前后端数据模型对齐说明

### 架构原则

本设计严格遵循"**契约驱动开发**"理念，后端数据模型严格按照前端 TypeScript 接口构建，实现零转换成本和完全类型对齐。

### 数据流架构

```
前端 TypeScript 接口 ← → 后端 Python 模型 ← → TradingView 库
     ↓                         ↓              ↓
  类型定义              Pydantic 模型      官方标准
  (单一事实来源)        (运行时验证)      (最终目标)
```

### 对齐策略

1. **类型严格对齐**
   - 前端 TypeScript 接口定义严格符合 TradingView 官方标准
   - 后端 Pydantic 模型 100% 对齐前端接口字段
   - 实现编译时和运行时双重类型验证

2. **零转换设计**
   - 后端直接输出 TradingView 兼容格式
   - 避免 datafeed 层进行数据转换
   - 减少错误源和性能开销

3. **契约驱动开发**
   - 前端接口变更自动影响后端实现
   - 通过类型系统保证一致性
   - API 文档与代码同步更新

### 对齐验证

**SymbolInfo 模型对齐度**: 100% ✅
- 所有必需字段严格匹配
- 可选字段完全覆盖
- 严格类型定义完全一致

**Bar 模型对齐度**: 100% ✅
- 字段名、类型、含义完全一致
- TradingView 标准完全兼容

**QuotesValue 模型对齐度**: 100% ✅
- 报价数据字段 100% 匹配
- 扩展字段支持完整实现

---

## 📚 参考资料

- [TradingView Charting Library 官方文档](https://www.tradingview.com/charting-library-docs/)
- [TradingView Datafeed API 文档](https://www.tradingview.com/charting-library-docs/latest/api/datafeed-api)
- [TradingView Platform 版本专用接口](https://www.tradingview.com/charting-library-docs/latest/trading_terminal/Watch-List)
- [WebSocket API 最佳实践](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
- [币安 WebSocket 文档](https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams)

---

**文档版本**: v16.1.0
**最后更新**: 2026年2月14日
**更新内容**:
- **v16.1.0**: 告警配置订阅优化
  - 移除 `SIGNAL:ALERT` 全局订阅，改为 `SIGNAL:{alert_id}` 精准订阅
  - 前端使用 UUIDv4 生成告警 ID
  - 创建告警请求添加 `id` 字段，由前端生成
  - 前端重连后需重新订阅
- **v16.2.0**: 账户订阅功能
  - 新增 ACCOUNT 订阅类型（BINANCE:ACCOUNT@SPOT, BINANCE:ACCOUNT@FUTURES）
  - 账户订阅采用增量数据推送，前端需先 GET 完整数据再订阅增量
- **v16.0.0**: 告警配置系统集成
  - 新增告警配置管理消息类型（create_alert_config, list_alert_configs, update_alert_config, delete_alert_config, enable_alert_config, list_signals）
  - 新增实时信号推送（signal_new）和订阅通道（SIGNAL:ALERT, SIGNAL:{alert_id}）
  - 告警配置格式与现有 WebSocket API 协议完全统一
- **v15.4.0**: GET类型命名优化
  - `list_subscriptions` 改为 `subscriptions`，风格与其他类型统一
- **v15.3.0**: 修复API响应格式不统一问题
  - **`type` 字段统一移至 `data` 内部**，与请求格式保持一致
  - 修复所有响应示例中的 `type` 字段位置
  - 确保请求和响应格式完全对称，降低前端解析复杂度
- **v15.2.0**: 统一WebSocket API响应格式
  - 修复任务完成响应格式不一致问题
  - 新增 `TaskResultData` 模型用于任务完成响应
  - 使用 Pydantic 数据模型替代硬编码字典
- **v15.1.0**: 任务通知优化 - 减少数据库查询
  - task_completed 通知包含 payload（requestId）和 result
  - API 网关无需再查询 tasks 表获取这些信息
  - 优化后除 get_klines 外无需额外数据库查询
- **v15.0.0**: 移除任务系统设计章节（移至 DATABASE_COORDINATED_ARCHITECTURE.md）
- **v14.0.0**: 前后端数据模型完全对齐
  - 新增完整数据模型详细字段定义章节
  - SymbolInfo、Bar、QuotesValue 模型严格对齐前端 TypeScript 接口
  - 添加契约驱动开发架构说明
  - 完善 resolve_symbol 响应示例，包含所有字段
  - 实现 100% 类型对齐，零转换成本
- **v13.3.0**: 批量订阅优化与格式规范
  - 移除v1.0字典格式支持，仅支持v2.0数组格式
  - 优化批量订阅速率限制：每包最多50个流，250ms间隔（4次/秒）
  - 遵守币安WebSocket API的5 msg/s限制，留出ping包空间
  - 提升批量订阅处理效率和性能
- **v13.2.0**: 订阅键格式优化 - 大小写一致性改进
  - 前端发送的订阅键格式与内部存储格式完全一致
  - 移除不必要的字符串大小写转换
  - 数据类型使用全大写格式（KLINE、TRADE、TICKER等）
  - 简化订阅处理流程，提升性能和可读性
- **v13.1.0**: 设计改进 - 采用币安风格，去掉ack概念混淆
  - 将"ack"响应改为"success"响应
  - 明确区分数据响应（包含实际内容）和确认消息（空data）
  - 借鉴币安WebSocket API的简洁设计风格
  - 添加success action的语义说明，提升开发者体验
- **v13.0.0**: 文档重构 - 专注于API规范设计
  - 移除所有Python代码实现
  - 保留JSON消息格式示例
  - 简化架构描述，专注于契约设计
  - 分离API规范与实现细节
- **v12.1.0**: Quotes 报价数据替换 MiniTicker 设计
- **v12.0.0**: 语义化交易对命名与永续期货支持
- **v11.0.0**: 统一管理器架构文档更新
- **v10.0.0**: 重大架构升级 - 纯 WebSocket 架构
**作者**: Claude Assistant
