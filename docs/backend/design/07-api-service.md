# API 服务规范设计（WebSocket 协议 + 数据模型）

本文档描述 API 服务的完整设计规范，包括 **WebSocket 协议设计**和 **Pydantic 数据模型实现**。

---

## 文档结构

1. [WebSocket 协议设计](./07-websocket-protocol.md) - 消息协议、订阅机制、错误处理
2. [数据模型实现](./08-api-models.md) - Pydantic 模型定义

> **说明**：协议设计与模型实现分离，07 侧重设计规范，08 侧重代码实现。

---

## 版本信息

**本文档版本**: v1.1
**最后更新**: 2026-03-02
**更新内容**: 新增交易功能架构说明

---

## 快速索引

### WebSocket 协议（设计）

- [架构设计](./07-websocket-protocol.md#-架构设计)
- [WebSocket 端点](./07-websocket-protocol.md#-websocket-端点)
- [统一消息协议](./07-websocket-protocol.md#-统一消息协议)
- [消息类型详解](./07-websocket-protocol.md#-消息类型详解)
- [语义化交易对命名](./07-websocket-protocol.md#-语义化交易对命名规范)
- [错误处理](./07-websocket-protocol.md#-错误处理-1)

### 数据模型（实现）

- [模型目录结构](./08-api-models.md#模型目录结构)
- [trading/ 交易数据模型](./08-api-models.md#trading-交易数据模型)
- [db/ 数据库模型](./08-api-models.md#db-数据库表对应模型)
- [protocol/ 协议层模型](./08-api-models.md#protocol-websocket-协议层模型)
- [error_models.py 错误模型](./08-api-models.md#error_modelspy-错误模型)

### 交易功能

- [交易订单表设计](./04-trading-orders.md) - trading_orders表结构
- [WebSocket协议-交易类型](./07-websocket-protocol.md#交易类型binance-service) - 交易消息类型定义

### API服务内部组件

- [DataProcessor](./04-dataprocessor.md) - 统一数据处理中心，监听数据库通知并推送数据

---

## 核心概念

### 协议版本

当前协议版本: **2.0**

```json
{
    "protocolVersion": "2.0"
}
```

### 消息流程

```
请求 → ACK 确认 → SUCCESS/ERROR 响应
      ↓
   实时数据推送 (UPDATE)
```

### 订阅键格式

```
{EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]
```

示例:
- `BINANCE:BTCUSDT@KLINE_1` - 1分钟K线
- `BINANCE:BTCUSDT@QUOTES` - 实时报价
- `BINANCE:BTCUSDT.PERP@KLINE_60` - 永续合约1小时K线

---

## 相关文档

- [DATABASE_COORDINATED_ARCHITECTURE.md](./DATABASE_COORDINATED_ARCHITECTURE.md) - 数据库协调架构
- [QUANT_TRADING_SYSTEM_ARCHITECTURE.md](./QUANT_TRADING_SYSTEM_ARCHITECTURE.md) - 系统架构详细设计
- [04-trading-orders.md](./04-trading-orders.md) - 交易订单表设计
- [04-dataprocessor.md](./04-dataprocessor.md) - DataProcessor统一数据处理中心
