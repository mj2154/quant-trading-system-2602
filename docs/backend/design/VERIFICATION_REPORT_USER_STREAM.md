# 用户数据流订阅验证报告

**日期**: 2026-03-20
**验证目标**: 验证现货和期货用户数据 WebSocket 订阅功能可行性

---

## 验证结论

| 服务 | 状态 | 订阅方式 |
|------|------|----------|
| **现货 (Spot)** | ✅ 可用 | WebSocket API + session.logon |
| **期货 (Futures)** | ✅ 可用 | listenKey 方式 |

---

## 现货用户数据订阅 (WebSocket API 方式)

### 端点

| 环境 | 端点 |
|------|------|
| **Demo Mode** | `wss://demo-ws-api.binance.com/ws-api/v3` |
| **Production** | `wss://ws-api.binance.com/ws-api/v3` |

### 订阅流程

1. **连接 WebSocket API**
2. **session.logon 认证** (Ed25519 签名)

   ```python
   timestamp = int(time.time() * 1000)
   auth_params = {"apiKey": api_key, "timestamp": timestamp}
   sorted_params = dict(sorted(auth_params.items()))
   payload = "&".join(f"{k}={v}" for k, v in sorted_params.items())
   signature = Ed25519Signer(private_key_pem).sign(payload)

   auth_request = {
       "id": "1",
       "method": "session.logon",
       "params": {
           "apiKey": api_key,
           "timestamp": timestamp,
           "signature": signature,
       },
   }
   ```

3. **userDataStream.subscribe 订阅** (无需参数)

   ```python
   subscribe_request = {
       "id": "2",
       "method": "userDataStream.subscribe",
       "params": {},
   }
   ```

### 事件格式

```json
{
    "subscriptionId": 0,
    "event": {
        "e": "executionReport",        // 订单更新
        "E": 1773970413980,           // 事件时间
        "s": "BTCUSDT",               // 交易对
        "c": "web_xxx",               // 客户端订单ID
        "S": "SELL",                  // 方向
        "o": "MARKET",                // 订单类型
        "x": "TRADE",                 // 执行类型
        "X": "FILLED",                // 订单状态
        "q": "0.01271000",            // 订单数量
        "L": "70506.11000000",        // 成交价格
        ...
    }
}
```

或

```json
{
    "subscriptionId": 0,
    "event": {
        "e": "outboundAccountPosition",  // 账户余额更新
        "E": 1773970413981,
        "u": 1773970413980,
        "B": [
            {"a": "BTC", "f": "0.01271867", "l": "0.00000000"},
            {"a": "USDT", "f": "4186.51821424", "l": "0.00000000"}
        ]
    }
}
```

### 关键发现

1. **session.logon 后直接 subscribe，无需获取 listenKey**
2. **事件格式**: `{"subscriptionId": 0, "event": {...}}`，不是 `{"stream": "userDataStream", "data": {...}}`
3. **Ed25519 签名**: payload 为 `apiKey=xxx&timestamp=xxx`（按字母顺序排序）

---

## 期货用户数据订阅 (listenKey 方式)

### 端点

| 环境 | 端点 |
|------|------|
| **Demo Mode** | `https://demo-fapi.binance.com` + `wss://dstream.binance.com/ws/<listenKey>` |

### 订阅流程

1. **HTTP POST 创建 listenKey**

   ```python
   POST https://demo-fapi.binance.com/fapi/v1/listenKey
   Headers: {"X-MBX-APIKEY": api_key}
   Response: {"listenKey": "xxx"}
   ```

2. **WebSocket 连接**

   ```
   wss://dstream.binance.com/ws/<listenKey>
   ```

3. **续期** (每 55 分钟)

   ```python
   PUT https://demo-fapi.binance.com/fapi/v1/listenKey
   ```

4. **关闭**

   ```python
   DELETE https://demo-fapi.binance.com/fapi/v1/listenKey?listenKey=xxx
   ```

### 事件格式

```json
{
    "e": "ACCOUNT_UPDATE",        // 账户更新
    "E": 1234567890,              // 事件时间
    "T": 1234567890,              // 事务时间
    "a": {
        "B": [{"a": "USDT", "wb": "122.1"}],  // 余额
        "P": [{"s": "BTCUSDT", "pa": "1"}]    // 持仓
    }
}
```

或

```json
{
    "e": "ORDER_TRADE_UPDATE",    // 订单成交更新
    ...
}
```

---

## 错误排查记录

### 1. 现货 WebSocket API 认证失败 (-2015)

**错误**: `{"status": 401, "error": {"code": -2015, "msg": "Invalid API-key, IP, or permissions for action"}}`

**原因**: 使用了错误的端点 (testnet 而非 demo)

**解决**: Demo Mode 应使用 `wss://demo-ws-api.binance.com/ws-api/v3`

### 2. 事件解析错误

**问题**: 代码预期 `{"stream": "userDataStream", "data": {...}}`

**实际**: `{"subscriptionId": 0, "event": {...}}`

**解决**: 根据实际收到的消息格式调整解析逻辑

---

## 教训总结

1. **不要轻信网上搜到的信息**：Context7 MCP 返回的文档说 listenKey REST API 已废弃，但 Demo Mode 的现货仍然需要使用 WebSocket API 方式

2. **官方文档优先**：币安本地文档 (`/home/ppadmin/code/binance-docs/`) 比网络搜索更准确

3. **端点必须匹配环境**：
   - Demo Mode API Key → Demo Mode 端点
   - Testnet API Key → Testnet 端点
   - 不能混用

4. **事件格式以实际收到为准**：文档描述的格式可能与实际略有差异，需要调试验证

5. **先验证再实施**：在启用 `AccountSubscriptionService` 之前，独立验证脚本可以快速定位问题

---

## 相关文件

- 验证脚本: `src/verify_user_stream.py`
- 现货客户端: `src/clients/spot_user_stream_client.py` ✅ 已重写为 WebSocket API 方式
- 期货客户端: `src/clients/futures_user_stream_client.py` (listenKey 方式)
- 用户数据订阅服务: `src/services/account_subscription_service.py`

---

## 2026-03-20 更新：现货客户端重写完成

### 实现要点

1. **继承 BaseWSClient**：统一客户端模式，只负责连接、接收、打包、发送
2. **session.logon 认证**：Ed25519 签名，建立会话级认证
3. **userDataStream.subscribe**：订阅用户数据流
4. **无 listenKey**：无需 listenKey，无需续期

### 事件格式

现货 WebSocket API 事件格式：
```json
{
    "subscriptionId": 0,
    "event": {
        "e": "executionReport",     // 事件类型
        "E": 1773970413980,        // 事件时间
        "s": "BTCUSDT",           // 交易对
        "c": "web_xxx",           // 客户端订单ID
        "S": "SELL",              // 方向
        "o": "MARKET",           // 订单类型
        "x": "TRADE",            // 执行类型
        "X": "FILLED",           // 订单状态
        ...
    }
}
```

### 收到的事件类型

| 事件类型 | 说明 | 触发场景 |
|---------|------|---------|
| `executionReport` | 订单更新 | 下单、撤单、成交 |
| `outboundAccountPosition` | 账户余额变化 | 余额变动 |
| `balanceUpdate` | 余额变动 | 充值、提取、划转 |
| `listStatus` | 订单列表状态 | OCO 订单状态变更 |

---

## 下一步

1. ✅ 现货 `SpotUserStreamClient` 已重写完成
2. ✅ `AccountSubscriptionService` 已更新以适配新客户端
3. 集成测试：在完整服务中验证现货用户数据订阅
