"""
E2E 测试

## 协议格式（严格遵循 07-websocket-protocol.md）

### 消息结构

```json
{
    "protocolVersion": "2.0",
    "type": "SUBSCRIBE",           // 消息类型（顶层）
    "requestId": "550e8400...",    // UUID v4 hex (32字符)
    "timestamp": 1704067200000,     // 时间戳（毫秒）
    "data": { ... }                 // 数据内容
}
```

### 三阶段消息流程

| 阶段 | type | requestId | 说明 |
|------|------|-----------|------|
| 1. 请求 | SUBSCRIBE/GET_CONFIG/... | ✅ 有 | 客户端发送 |
| 2. ACK | ACK | ✅ 有 | 服务端确认收到 |
| 3. SUCCESS | SUBSCRIPTION_DATA/CONFIG_DATA/... | ✅ 有 | 服务端返回结果 |
| 4. UPDATE | UPDATE | ❌ 无 | 服务端主动推送（实时数据） |

### 关键区别

**ACK/SUCCESS 响应**：
- 包含 `requestId`（用于关联请求和响应）
- `type` 在顶层

**UPDATE 推送**：
- **不包含** `requestId`（协议明确规定）
- `type="UPDATE"` 在顶层
- 包含 `subscriptionKey` 和 `content`

## 运行测试

```bash
cd services/api-service

# 运行所有 E2E 测试
pytest tests/e2e/ -v

# 按类型运行
pytest tests/e2e/ -m "spot and ws" -v   # 现货 WebSocket
pytest tests/e2e/ -m "spot and rest" -v  # 现货 REST
pytest tests/e2e/ -m "realtime" -v       # 实时数据测试

# 只运行 REST 测试（当前可用）
pytest tests/e2e/spot/rest/ -v
```

## 测试状态

| 测试类型 | 状态 | 说明 |
|----------|------|------|
| REST (config, klines, quotes) | ✅ 通过 | 协议格式正确 |
| WebSocket 订阅 | ❌ 失败 | 需要配置binance-service的WebSocket推送 |
| search_symbols | ⏭️ 跳过 | API返回INTERNAL_ERROR |

## Fixtures

| Fixture | 说明 |
|---------|------|
| ws_client | 独立 WebSocket 连接 |
| ws_connected_client | 已连接 WebSocket 客户端 |

## 标记

| 标记 | 说明 |
|------|------|
| @pytest.mark.spot | 现货测试 |
| @pytest.mark.futures | 期货测试 |
| @pytest.mark.rest | REST API 测试 |
| @pytest.mark.ws | WebSocket 测试 |
| @pytest.mark.realtime | 实时数据推送测试 |
| @pytest.mark.slow | 慢速测试 |
