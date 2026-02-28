# TradingView API 规范符合度报告

**生成日期**: 2026-02-10
**分析范围**: `docs/architecture/design/TradingView-完整API规范设计文档.md` vs `services/api-service/tests/e2e/`
**分析人员**: Claude Code (规范分析师)

---

## 执行摘要

本报告对 TradingView API 规范文档与测试代码进行了详细的符合度分析。

**总体评估**: ⚠️ **部分符合** - 测试代码在核心验证逻辑上基本符合规范，但在字段命名和格式细节上存在多处偏差。

---

## 1. v2.1 统一响应格式验证

### 1.1 核心要求对比

| 要求项 | 规范定义 | 测试代码实现 | 状态 |
|--------|----------|-------------|------|
| `type` 字段位置 | `data.type` | `data.type` | ✅ 符合 |
| `protocolVersion` 存在 | `"2.0"` | `"2.0"` | ✅ 符合 |
| `requestId` 存在 | 必需 | 必需 | ✅ 符合 |
| `timestamp` 存在 | 必需（毫秒） | 必需 | ⚠️ 部分符合 |
| `action` 有效值 | get/subscribe/unsubscribe/success/update/error | 同左 | ✅ 符合 |

### 1.2 timestamp 字段问题

**问题**: 测试代码中存在时间戳格式不一致

- `base_simple_test.py:67`: 使用秒级时间戳 `int(time.time())`
- `base_e2e_test.py:100`: 使用毫秒级时间戳 `int(time.time() * 1000)`

**规范要求**: timestamp 必须是毫秒级（Unix时间戳，毫秒）

**影响**: 测试客户端发送的请求可能与服务端期望不一致

---

## 2. 订阅键格式验证

### 2.1 v2.0 订阅键格式

**规范定义**:
```
{EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]
```

**测试验证**: ✅ 基本符合

| 测试用例 | 规范示例 | 状态 |
|----------|----------|------|
| KLINE | `BINANCE:BTCUSDT@KLINE_1` | ✅ |
| QUOTES | `BINANCE:BTCUSDT@QUOTES` | ✅ |
| TRADE | `BINANCE:BTCUSDT@TRADE` | ✅ |
| 永续合约 | `BINANCE:BTCUSDT.PERP@KLINE_1` | ✅ |

### 2.2 数据类型全大写要求

**规范要求**: `KLINE`, `QUOTES`, `TRADE`（全大写）

**测试代码**: ✅ 正确验证全大写格式

正则表达式验证：
```python
r"^[A-Z]+:[A-Z0-9]+(\.[A-Z0-9]+)?@(KLINE|QUOTES|TRADE)(_[0-9A-Z]+)?$"
```

---

## 3. 实时数据推送格式

### 3.1 `content` vs `payload` 字段问题

**规范定义** (v2.1):
```json
{
    "data": {
        "subscriptionKey": "BINANCE:BTCUSDT@KLINE_1",
        "content": {  // 使用 content
            "time": 1703123400000,
            "open": 97000.00,
            ...
        }
    }
}
```

**测试代码问题** (`base_simple_test.py:338-346`):

```python
# 后端使用 payload，设计文档规定使用 content
# 兼容两种格式
if "content" in data_content:
    content = data_content.get("content", {})
elif "payload" in data_content:
    content = data_content.get("payload", {})
else:
    content = {}
```

**分析**:
- 测试代码同时支持 `content` 和 `payload` 两种格式
- 规范明确定义使用 `content` 字段（避免与数据库 tasks 表的 payload 混淆）
- **实际后端实现可能仍在使用 `payload`**

**建议**: 确认后端实现并统一为 `content`

### 3.2 K线推送格式

**规范定义**:
```json
{
    "data": {
        "subscriptionKey": "BINANCE:BTCUSDT@KLINE_1",
        "content": {
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

**测试验证** (`assert_kline_payload_format`):
- ✅ 验证必填字段: time, open, high, low, close
- ✅ 验证字段类型为数值
- ✅ volume 可选验证

### 3.3 Quotes推送格式

**规范定义**:
```json
{
    "data": {
        "subscriptionKey": "BINANCE:BTCUSDT@QUOTES",
        "content": {
            "n": "BINANCE:BTCUSDT",
            "s": "ok",
            "v": {
                "ch": 123.45,
                "chp": 2.35,
                "lp": 97500.00,
                ...
            }
        }
    }
}
```

**测试验证** (`assert_quotes_payload_format`):
- ✅ 验证 n, s, v 字段存在
- ✅ 验证 v 为字典类型
- ✅ 验证必填字段: ch, chp, lp, ask, bid, spread, volume

**⚠️ 问题**: 规范中 `ask`, `bid`, `spread`, `volume` 是**推荐字段**而非必填，测试代码要求全部必填可能过于严格。

---

## 4. 三阶段消息流程验证

### 4.1 流程定义

| 阶段 | action | 说明 |
|------|--------|------|
| 1 | get/subscribe/unsubscribe | 客户端发送请求 |
| 2 | ack | 服务端确认收到请求 |
| 3 | success/error | 服务端返回结果 |

### 4.2 测试代码实现

**问题识别**:

1. **ack 响应格式不一致**
   - `base_e2e_test.py:319` 注释: `{"action": "ack", "requestId": "req_xxx", "data": {"message": "..."}}`
   - 规范 v2.1: `data` 应为空对象 `{}`

2. **wait_for_task_completion 方法** (`base_e2e_test.py:307-370`)
   - 直接跳过 ack 等待 success
   - 对于 `klines`, `quotes`, `config`, `search_symbols`, `subscriptions` 类型直接返回

### 4.3 规范符合度评估

| 要求 | 测试代码实现 | 状态 |
|------|-------------|------|
| ack 确认包含 requestId | ✅ 正确 | ✅ |
| success 响应包含 requestId | ✅ 正确 | ✅ |
| update 消息不包含 requestId | ✅ 正确 | ✅ |
| ack 的 data 为空对象 `{}` | ⚠️ 可能有 message 字段 | ❌ |

---

## 5. Quotes 数据格式详细分析

### 5.1 规范 vs 测试验证

**规范定义 Quotes v 对象字段**:

| 字段 | 类型 | 必填 | 测试验证 |
|------|------|------|----------|
| ch | number | ❌ | ✅ 必填 |
| chp | number | ❌ | ✅ 必填 |
| lp | number | ❌ | ✅ 必填 |
| ask | number | ❌ | ✅ 必填 |
| bid | number | ❌ | ✅ 必填 |
| spread | number | ❌ | ✅ 必填 |
| open_price | number | ❌ | ✅ 推荐 |
| high_price | number | ❌ | ✅ 推荐 |
| low_price | number | ❌ | ✅ 推荐 |
| prev_close_price | number | ❌ | ✅ 推荐 |
| volume | number | ❌ | ✅ 必填 |

**问题**: 测试代码将 `ask`, `bid`, `spread`, `volume` 标记为必填，但规范中这些是**可选字段**。

**建议**: 调整测试验证逻辑，将 `lp` 以外的字段设为推荐验证。

---

## 6. 错误码定义验证

### 6.1 规范定义错误码

| 错误码 | 说明 |
|--------|------|
| INVALID_SYMBOL | 交易对不存在或不支持 |
| INVALID_INTERVAL | 分辨率不支持 |
| INVALID_DATE_RANGE | 无效的日期范围 |
| EXCHANGE_NOT_FOUND | 交易所不存在 |
| RATE_LIMIT_EXCEEDED | 请求频率超限 |
| INTERNAL_ERROR | 服务器内部错误 |
| SERVICE_UNAVAILABLE | 服务暂时不可用 |
| INVALID_SYMBOLS | 无效的交易对列表 |
| SYMBOL_NOT_FOUND | 交易对不存在 |
| EXCHANGE_NOT_SUPPORTED | 交易所不支持 |
| SUBSCRIPTION_NOT_FOUND | 订阅不存在 |
| TIMEOUT | 请求超时 |
| UNKNOWN_ACTION | 未知动作类型 |
| INVALID_PARAMETERS | 参数错误 |

### 6.2 测试代码验证

**`assert_error_response_format`** 方法验证:
- ✅ 验证 action 为 "error"
- ✅ 验证 data.errorCode 存在
- ✅ 验证 data.errorMessage 存在
- ✅ 验证字段类型为字符串

---

## 7. 偏差清单

### 7.1 高优先级问题（需立即修复）

| # | 问题描述 | 位置 | 建议修复 |
|---|----------|------|----------|
| 1 | `content` vs `payload` 字段不统一 | `base_simple_test.py:338-346` | 确认后端实现，统一为 `content` |
| 2 | ack 响应可能包含 message 字段 | `base_e2e_test.py:319` 注释 | 确认 ack 的 data 为空对象 `{}` |
| 3 | timestamp 格式不一致 | `base_simple_test.py:67` | 统一使用毫秒级时间戳 |

### 7.2 中优先级问题（建议修复）

| # | 问题描述 | 位置 | 建议修复 |
|---|----------|------|----------|
| 4 | Quotes 字段验证过于严格 | `base_simple_test.py:371-376` | 只要求 lp 必填，其他推荐 |
| 5 | 缺少 `isBarClosed` 字段验证 | `assert_kline_payload_format` | K线推送应包含 `isBarClosed` |

### 7.3 低优先级问题（可选优化）

| # | 问题描述 | 位置 | 建议修复 |
|---|----------|------|----------|
| 6 | 缺少 TRADE 数据格式测试 | - | 添加 TRADE 推送格式验证 |
| 7 | 缺少批量 Quotes 推送测试 | - | 添加批量格式验证 |

---

## 8. 规范符合度检查清单

### 8.1 消息格式

- [x] protocolVersion 存在且为 "2.0"
- [x] action 值有效
- [x] requestId 存在于请求/响应
- [x] timestamp 存在（毫秒）
- [x] data.type 在 data 内部（success/error/update）
- [x] data 字段存在

### 8.2 订阅键格式

- [x] 格式: `{EXCHANGE}:{SYMBOL}[.{后缀}]@{DATA_TYPE}[_{INTERVAL}]`
- [x] 数据类型全大写: KLINE, QUOTES, TRADE
- [x] 支持永续合约后缀: .PERP

### 8.3 K线数据格式

- [x] 字段: time, open, high, low, close
- [x] time 为毫秒时间戳
- [x] 价格字段为数值类型
- [x] volume 可选

### 8.4 Quotes数据格式

- [x] n: 符号名称
- [x] s: 状态 (ok/error)
- [x] v: 报价对象
- [x] v.lp: 最新价格

---

## 9. 结论与建议

### 9.1 总体评估

测试代码在核心验证逻辑上**基本符合** TradingView API 规范，但在以下方面存在偏差：

1. **字段命名统一性**: `content` vs `payload`
2. **时间戳格式**: 秒级 vs 毫秒级
3. **字段必填性**: 部分推荐字段被误判为必填

### 9.2 建议行动

**立即执行**:
1. 确认后端实现使用的字段名，统一为 `content`
2. 统一时间戳为毫秒级
3. 修正 ack 响应格式

**后续优化**:
1. 调整 Quotes 字段验证逻辑
2. 补充 TRADE 数据格式测试
3. 补充批量推送格式测试

---

**报告版本**: v1.0
**最后更新**: 2026-02-10
