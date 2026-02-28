# 币安服务数据模型设计统一重构计划

## 背景

API服务已完成数据模型重构，采用统一的命名规范和目录结构。币安服务的数据模型存在以下不一致：
- 基类命名与API服务不统一
- K线类命名风格不一致 (`KlineData` vs `KlineData`)
- 账户类命名不一致 (`BinanceAccountInfo` vs `SpotAccountInfo`)
- 存在未使用的重复代码
- 目录结构与API服务不一致

## 目标

确保币安服务的数据模型设计与API服务保持一致的设计理念。

---

## 一、设计文档修改

**文件**: `docs/backend/design/03-binance-service.md`

### 1. 更新 Pydantic 命名转换基类 (7.3节)

将示例代码中的基类统一为API服务的命名风格：

| 原命名 | 统一后 |
|--------|--------|
| `BinanceModel` | `SnakeCaseModel` |
| `ResponseModel` | `CamelCaseModel` |
| `InternalModel` | `InternalModel` (保留) |

### 2. 添加命名风格规范 (新增7.4节)

```
### 7.4 命名风格规范

与API服务保持一致的命名风格：

| 类型 | 命名风格 | 示例 |
|------|----------|------|
| K线类 | KlineXxx (l小写) | KlineData, KlineBar, KlineBars |
| 报价类 | QuotesXxx | QuotesValue, QuotesData |
| 账户类 | XxxAccountInfo | SpotAccountInfo, FuturesAccountInfo |
| 文件名 | snake_case | kline_models.py, quote_models.py |

> 注意：K线类统一使用 KlineXxx（小写l）风格。
```

### 3. 添加目录结构规范 (新增7.5节)

```
### 7.5 数据模型目录结构

币安服务采用扁平化结构，根据数据来源划分：

models/
├── __init__.py           # 统一导出
├── base.py              # 基类定义（SnakeCaseModel, CamelCaseModel）
├── kline_models.py      # K线数据模型（API响应 + 数据库）
├── ticker_models.py     # 行情数据模型（API响应）
├── account_models.py    # 账户数据模型（API响应 + 数据库）
└── exchange_models.py   # 交易所信息模型（API响应 + 数据库）
```

> 说明：币安服务是数据采集服务，目录结构按数据类型扁平划分，无需API服务的 db/trading/protocol 分层。

---

## 二、代码修改

### 修改1: 基类重命名

**文件**: `services/binance-service/src/models/base.py`

```python
# 修改前                    # 修改后
class BinanceModel     →   class SnakeCaseModel
class ResponseModel    →   class CamelCaseModel
class InternalModel   →   class InternalModel (保留)
```

### 修改2: 删除重复代码

**文件**: `services/binance-service/src/models/unified_models.py`

- 该文件定义的 `KlineBar`, `KlineBars`, `QuotesData` 从未被使用
- 直接删除文件，并从 `__init__.py` 中移除导入

### 修改3: K线类命名统一

**文件**: `services/binance-service/src/models/binance_kline.py`

| 原类名 | 统一后 |
|--------|--------|
| `KlineData` | `KlineData` |
| `KlineCreate` | `KlineCreate` |
| `KlineResponse` | `KlineResponse` |
| `KlineWebSocketData` | `KlineWebSocketData` |
| `KlineWebSocket` | `KlineWebSocket` |
| `KlineInterval` | `KlineInterval` |

同时将文件名改为: `kline_models.py`

### 修改4: 账户类命名统一

**文件**: `services/binance-service/src/models/spot_account.py`

| 原类名 | 统一后 |
|--------|--------|
| `BinanceCommissionRates` | `CommissionRates` |
| `BinanceBalance` | `Balance` |
| `BinanceAccountInfo` | `SpotAccountInfo` |

**文件**: `services/binance-service/src/models/futures_account.py`

| 原类名 | 统一后 |
|--------|--------|
| `FuturesAsset` | `FuturesAsset` (保留) |
| `FuturesPosition` | `FuturesPosition` (保留) |
| `FuturesAccountInfo` | `FuturesAccountInfo` (保留) |

### 修改5: 行情类命名调整

**文件**: `services/binance-service/src/models/ticker.py`

将 `Ticker24hrSpot`, `Ticker24hrFutures` 等类继承基类统一为 `SnakeCaseModel`

### 修改6: 更新 __init__.py 导出

**文件**: `services/binance-service/src/models/__init__.py`

- 移除对 `unified_models` 的导入
- 更新类名引用

---

## 三、验证方式

1. **静态检查**: 运行 `ruff check services/binance-service/src/models/`
2. **导入测试**: `cd services/binance-service && uv run python -c "from models import *"`
3. **类型检查**: `cd services/binance-service && uv run python -m pyright src/models/`

---

## 四、受影响文件清单

| 文件 | 操作 |
|------|------|
| `docs/backend/design/03-binance-service.md` | 修改 |
| `services/binance-service/src/models/base.py` | 修改 |
| `services/binance-service/src/models/unified_models.py` | 删除 |
| `services/binance-service/src/models/binance_kline.py` | 重命名文件 + 修改类名 |
| `services/binance-service/src/models/spot_account.py` | 修改类名 |
| `services/binance-service/src/models/ticker.py` | 修改基类引用 |
| `services/binance-service/src/models/__init__.py` | 修改导入 |

---

## 五、当前代码问题详细说明

### 5.1 基类命名不一致

| 服务 | 输入模型基类 | 输出模型基类 | 内部模型基类 |
|------|-------------|-------------|-------------|
| API服务 | `SnakeCaseModel` | `CamelCaseModel` | (无专用基类) |
| 币安服务 | `BinanceModel` | `ResponseModel` | `InternalModel` |

**问题**: 语义不清晰，`BinanceModel` 限制了通用性

### 5.2 K线类命名不一致

| API服务 | 币安服务 |
|--------|---------|
| `KlineBar` | - |
| `KlineData` | `KlineData` |
| `KlineBars` | - |
| `KlineResponse` | `KlineResponse` |

**问题**: 命名风格正确，但需确认API服务与币安服务保持一致

### 5.3 账户类命名不一致

| API服务 | 币安服务 |
|--------|---------|
| `SpotAccountInfo` | `BinanceAccountInfo` |
| `FuturesAccountInfo` | `FuturesAccountInfo` |

**问题**: 一个带 `Binance` 前缀，一个不带，不对称

### 5.4 未使用的重复代码

`unified_models.py` 包含以下从未被引用的模型：
- `KlineBar`
- `KlineBars`
- `QuotesData`

这些模型在API服务中已定义，币安服务存在重复代码。

---

## 六、API服务命名规范参考

### 6.1 基类定义

```python
# API服务: services/api-service/src/models/base.py
class CamelCaseModel(BaseModel):
    """响应模型基类 - 序列化时自动转为 camelCase"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

class SnakeCaseModel(BaseModel):
    """请求模型基类 - 接收 camelCase 自动转为 snake_case"""
    model_config = ConfigDict(
        alias_generator=to_snake,
        populate_by_name=True,
    )
```

### 6.2 类命名风格

- K线相关: `KlineXxx` (l小写)
- 报价: `QuotesXxx`
- 账户: `XxxAccountInfo`
- 文件名: `snake_case` (如 `kline_models.py`)

### 6.3 命名风格说明

API服务统一使用 `KlineXxx`（小写l）风格，理由：
- 与数据库字段风格保持一致（snake_case）
- 简洁统一，避免与其他命名风格混淆
