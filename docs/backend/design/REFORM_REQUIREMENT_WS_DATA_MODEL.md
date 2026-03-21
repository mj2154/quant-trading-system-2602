# WS 实时数据模型重构需求报告

> **日期**: 2026-03-21
> **状态**: 已审核
> **优先级**: 高

---

## 1. 背景与问题

### 1.1 问题描述

`SnakeCaseModel` 的 `convert_camel_to_snake` 验证器存在设计缺陷，无法正确处理币安 WebSocket 的**极端简写字段名**场景。

**问题 1: `E` 和 `e` 会被 `to_snake` 转换为相同的键**
```python
to_snake("E")  # => "e"
to_snake("e")  # => "e"
# 两者冲突！
```

**问题 2: 当数据同时包含单字母键和多字符 camelCase 键时，camelCase 键不被转换**
```python
# 当数据同时包含单字母键和 camelCase 键时：
{'eventTime': 123, 'E': 456}
# 结果: {'eventTime': 123, 'E': 456}  # eventTime 未被转换！
```

### 1.2 根本原因

`SnakeCaseModel` + `to_snake` 的组合是为**通用场景**设计的，不适用于币安 WebSocket 的**极端简写字段名**场景。

币安 WS 数据大量使用单字母字段：
- `e` = event type
- `E` = event time
- `s` = symbol
- `t` = start time (kline open)
- `T` = end time (kline close)
- `o` = open price
- `c` = close price
- `h` = high price
- `l` = low price
- `v` = volume
- `q` = quote volume
- `n` = number of trades

### 1.3 GET vs WS 数据格式差异

| 数据来源 | 字段命名风格 | 示例 |
|----------|-------------|------|
| GET HTTP API | camelCase | `priceChange`, `openPrice`, `closeTime` |
| WS 订阅推送 | 单字母简写 | `c`, `h`, `l`, `o`, `t`, `T`, `v` |

---

## 2. 设计方案

### 2.1 核心原则

**GET 数据和 WS 订阅数据分开定义独立的数据模型**

| 数据类型 | 模型特点 | 字段转换 |
|----------|----------|----------|
| GET HTTP 响应 | 使用 `SnakeCaseModel` + `alias` | camelCase → snake_case |
| WS 订阅推送 | 使用独立模型，直接定义 `alias` | **不转换**，保留原始单字母字段 |

### 2.2 推荐的模型设计（方案 A）

```python
# 不继承 SnakeCaseModel，直接继承 BaseModel
class BinanceWSKline(BaseModel):
    """币安 WebSocket K线原始数据模型

    特点：
    - 直接使用 alias 映射币安原始单字母字段
    - 不依赖 to_snake 自动转换
    - 字段名使用完整的 snake_case 语义名称
    """

    # 时间字段
    open_time: int = Field(alias="t", description="K线开始时间")
    close_time: int = Field(alias="T", description="K线结束时间")
    event_time: int = Field(alias="E", description="事件时间")

    # 交易对和间隔
    symbol: str = Field(alias="s", description="交易对符号")
    interval: str = Field(alias="i", description="K线间隔")

    # OHLC 价格
    open_price: Decimal = Field(alias="o", description="开盘价")
    close_price: Decimal = Field(alias="c", description="收盘价")
    high_price: Decimal = Field(alias="h", description="最高价")
    low_price: Decimal = Field(alias="l", description="最低价")

    # 成交量
    volume: Decimal = Field(alias="v", description="成交量")
    quote_volume: Decimal = Field(alias="q", description="成交额")

    # 交易统计
    number_of_trades: int = Field(alias="n", description="交易笔数")
    taker_buy_base_volume: Decimal = Field(alias="V", description="主动买入成交量")
    taker_buy_quote_volume: Decimal = Field(alias="Q", description="主动买入成交额")

    # K线状态
    is_closed: bool = Field(alias="x", description="K线是否已结束")

    model_config = ConfigDict(populate_by_name=True)


class BinanceWSKlineEvent(BaseModel):
    """币安 WebSocket K线事件 wrapper"""

    event_type: str = Field(alias="e")
    event_time: int = Field(alias="E")
    symbol: str = Field(alias="s")
    kline: BinanceWSKline = Field(alias="k")
```

---

## 3. 附录

### A. 币安 WS K线事件完整字段对照

| 字段 | 类型 | 说明 |
|------|------|------|
| `e` | string | 事件类型，如 "kline" |
| `E` | long | 事件时间（毫秒） |
| `s` | string | 交易对，如 "BTCUSDT" |
| `k` | object | K线数据对象 |
| `k.t` | long | K线开始时间 |
| `k.T` | long | K线结束时间 |
| `k.s` | string | 交易对 |
| `k.i` | string | K线间隔 |
| `k.o` | string | 开盘价 |
| `k.c` | string | 收盘价 |
| `k.h` | string | 最高价 |
| `k.l` | string | 最低价 |
| `k.v` | string | 成交量 |
| `k.q` | string | 成交额 |
| `k.x` | bool | K线是否已结束 |
| `k.n` | int | 交易笔数 |
| `k.V` | string | Taker买入成交量 |
| `k.Q` | string | Taker买入成交额 |
| `k.L` | int | 最后成交价 |
| `k.f` | int | 第一笔成交ID |
| `k.l` | int | 最后一笔成交ID |

### B. 参考资料

- `docs/binance-docs/binance_futures_docs/` - U本位合约 API 文档
- `docs/binance-docs/binance_spot_docs/` - 现货 API 文档
- `services/binance-service/src/models/base.py` - 模型基类定义
