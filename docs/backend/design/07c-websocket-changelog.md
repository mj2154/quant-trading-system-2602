# WebSocket API 版本变更记录

> 本文档记录 WebSocket API 协议的所有版本变更历史。

---

## v2.6 (2026-03-22)

- 🐛 **修复 subscriptionKey 位置** - 所有 UPDATE 消息的 subscriptionKey 已提升到顶层，与代码实现一致
  - K线推送
  - 报价推送
  - 信号推送
  - 用户数据增量推送（期货/现货）
  - 订单状态推送

## v2.5 (2026-03-06)

- 🚀 **补充现货特有可选参数** - 取消订单支持 newClientOrderId 和 cancelRestrictions 参数

## v2.4 (2026-03-06)

- 🚀 **订单数据模型重构** - 完全采用币安蛇形命名，与币安API格式完全一致
- 🚀 **newClientOrderId改为必填** - 前端独立生成，用于订单追踪
- 🚀 **requestId与newClientOrderId区分** - requestId用于WS请求追踪，newClientOrderId用于订单追踪
- 🚀 **去掉marketType字段** - 通过symbol前缀区分期货/现货（.PERP后缀为期货）
- 🚀 **取消/查询订单使用origClientOrderId** - 按币安规范，取消和查询时使用origClientOrderId字段

## v2.3 (2026-03-02)

- 🚀 **交易功能支持** - 新增交易消息类型 (CREATE_ORDER, GET_ORDER, LIST_ORDERS, CANCEL_ORDER, GET_OPEN_ORDERS)
- 🚀 **订单数据推送** - 新增 ORDER_UPDATE 订阅类型，支持订单状态实时推送

## v2.2 (2026-02-27)

- 🚀 **用户数据订阅支持** - 新增 USERDATA 订阅类型 (BINANCE:SPOT@USERDATA, BINANCE:FUTURES@USERDATA)
- 🚀 **增量数据推送** - 用户数据订阅采用"GET 完整 + 订阅增量"策略，前端需先 GET 初始化再订阅增量

## v2.1 (2026-02-10)

- 🚀 **Ack 响应精简** - data 改为空对象 `{}`，移除冗余 message 字段
- 🚀 **命名区分** - 实时推送使用 `content`，避免与数据库 tasks 表的 payload 混淆

## v2.0

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
