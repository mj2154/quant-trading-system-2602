# WebSocket API 错误处理

> 本文档定义 WebSocket API 的错误码体系和错误消息格式。

---

## 错误消息格式

所有错误响应均遵循统一格式：

```json
{
    "protocolVersion": "2.0",
    "type": "ERROR",
    "requestId": "550e8400e29b41d4a716446655440000",
    "timestamp": 1703123456790,
    "data": {
        "errorCode": "INVALID_SYMBOL",
        "errorMessage": "Symbol BINANCE:INVALID not found"
    }
}
```

## 错误码定义

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

> **数据模型说明**：详细的数据模型定义请参考 [08-api-models.md](./08-api-models.md)。
