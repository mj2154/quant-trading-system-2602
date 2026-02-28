# 测试策略

## 概述

本文档定义了量化交易系统的测试策略，包括单元测试、集成测试和端到端测试的要求与实施规范。

---

## 1. 测试原则

### 1.1 TDD优先原则

测试驱动开发（TDD）是本项目的核心开发方法：

1. **编写测试先于实现**：在编写功能代码之前，先编写失败的测试用例
2. **最小实现**：编写刚好能让测试通过的生产代码
3. **持续重构**：在确保测试通过的前提下，持续改进代码质量
4. **覆盖率要求**：核心业务逻辑必须达到 80% 以上覆盖率

### 1.2 测试隔离原则

- 每个服务独立测试，使用独立的测试数据库
- 测试之间无依赖，测试用例可以独立运行
- 使用测试夹具（fixtures）管理测试数据
- 使用 mock 对象隔离外部依赖

### 1.3 测试分层原则

```
┌─────────────────────────────────────────────────────────────┐
│                    E2E 测试 (关键业务流程)                     │
├─────────────────────────────────────────────────────────────┤
│               集成测试 (API、数据库、事件)                    │
├─────────────────────────────────────────────────────────────┤
│                  单元测试 (函数、类、模块)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 单元测试

### 2.1 测试范围

单元测试覆盖以下内容：

| 模块 | 测试内容 |
|------|----------|
| **策略计算** | 策略算法正确性、边界条件处理 |
| **数据转换** | 数据格式转换、字段映射 |
| **工具函数** | 通用函数、计算逻辑 |
| **数据模型** | 模型验证、序列化/反序列化 |

### 2.2 策略计算模块测试

策略计算是系统的核心模块，需要全面测试：

```python
import pytest
from unittest.mock import Mock, patch

# 测试策略返回 true/false/null
def test_random_strategy_signal_values():
    """随机策略应返回 true、false 或 None"""
    from src.strategies.random_strategy import RandomStrategy

    strategy = RandomStrategy()
    results = set()

    # 执行多次以覆盖所有可能的返回值
    for _ in range(100):
        input_data = StrategyInput(
            symbol="BTCUSDT",
            interval="60",
            kline_data={},
            subscription_key="BINANCE:BTCUSDT@KLINE_60",
            computed_at=datetime.utcnow()
        )
        output = strategy.calculate(input_data)
        results.add(output.signal_value)

    # 应包含 True、False、None
    assert True in results or False in results or None in results
```

### 2.3 数据筛选器测试

```python
def test_data_filter_by_subscription_key():
    """测试按订阅键筛选数据"""
    from src.services.filter import SubscriptionFilter

    filter = SubscriptionFilter()

    # 模拟订阅键列表
    subscriptions = [
        "BINANCE:BTCUSDT@KLINE_1m",
        "BINANCE:BTCUSDT@KLINE_60",
        "BINANCE:ETHUSDT@KLINE_60"
    ]

    # 筛选 BTCUSDT 相关的订阅
    btc_subscriptions = filter.filter_by_symbol(subscriptions, "BTCUSDT")

    assert len(btc_subscriptions) == 2
    assert "BINANCE:BTCUSDT@KLINE_1m" in btc_subscriptions
    assert "BINANCE:BTCUSDT@KLINE_60" in btc_subscriptions
```

### 2.4 信号写入器测试

```python
@pytest.mark.asyncio
async def test_signal_writer_insert():
    """测试信号写入数据库"""
    from src.services.signal_writer import SignalWriter

    mock_db = Mock()
    mock_repo = Mock()
    mock_db.repository = mock_repo

    writer = SignalWriter(mock_db)

    signal_data = {
        "alert_id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
        "symbol": "BINANCE:BTCUSDT",
        "signal_value": True,
        "computed_at": datetime.utcnow()
    }

    await writer.write(signal_data)

    mock_repo.insert.assert_called_once()
```

### 2.5 单元测试规范

- 每个测试函数专注于测试一个功能点
- 测试命名清晰，表达测试意图
- 使用 pytest fixtures 管理测试数据
- 使用 parametrize 进行参数化测试

---

## 3. 集成测试

### 3.1 测试范围

集成测试覆盖以下内容：

| 模块 | 测试内容 |
|------|----------|
| **信号服务** | 启动和订阅管理、通知监听 |
| **数据库操作** | CRUD 操作、事务处理 |
| **事件通信** | PostgreSQL NOTIFY/LISTEN |
| **API 接口** | REST/WebSocket 接口 |

### 3.2 信号服务启动和订阅管理

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_signal_service_subscription():
    """测试信号服务订阅管理"""
    from src.services.signal_service import SignalService
    from src.db.database import Database

    # 使用测试数据库
    db = Database(test_mode=True)

    service = SignalService(db)

    # 测试订阅确保逻辑
    strategies = [
        StrategyConfig(
            symbol="BTCUSDT",
            interval="60",
            strategy_type="macd_resonance"
        )
    ]

    await service.ensure_subscriptions(strategies)

    # 验证订阅已创建
    subscription = await service._realtime_repo.get_subscription(
        "BINANCE:BTCUSDT@KLINE_60"
    )
    assert subscription is not None
    assert "signal-service" in subscription.subscribers
```

### 3.3 realtime.update 通知监听

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_realtime_update_listener():
    """测试实时数据更新通知监听"""
    from src.listener.realtime_update_listener import RealtimeUpdateListener

    listener = RealtimeUpdateListener()

    # 模拟通知数据
    notification = {
        "event_id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
        "event_type": "realtime.update",
        "timestamp": "2026-02-21T10:00:00Z",
        "data": {
            "subscription_key": "BINANCE:BTCUSDT@KLINE_60",
            "data": {"k": {"o": "50000", "h": "51000", "l": "49000", "c": "50500"}},
            "is_closed": False
        }
    }

    received = []

    async def callback(data):
        received.append(data)

    listener.on_update(callback)

    # 触发通知
    await listener.handle(notification)

    assert len(received) == 1
    assert received[0]["subscription_key"] == "BINANCE:BTCUSDT@KLINE_60"
```

### 3.4 strategy_signals 表写入验证

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_strategy_signals_insert_trigger():
    """测试 strategy_signals 表写入触发通知"""
    from src.db.strategy_signals_repository import StrategySignalsRepository

    repo = StrategySignalsRepository(test_db)

    # 插入信号
    signal = await repo.insert(
        alert_id="0189a1b2-c3d4-5e6f-7890-abcd12345678",
        symbol="BINANCE:BTCUSDT",
        signal_value=True
    )

    assert signal.id is not None

    # 验证触发器已触发（通过监听通知）
    # 注意：这需要异步监听
```

### 3.5 signal.new 通知触发验证

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_signal_new_notification():
    """测试 signal.new 事件通知"""
    # 订阅 signal.new 频道
    notification_received = []

    async def on_notification(payload):
        notification_received.append(payload)

    await listen_channel("signal.new", on_notification)

    # 插入信号数据（触发 trigger_strategy_signals_new）
    await test_db.execute("""
        INSERT INTO strategy_signals (alert_id, symbol, signal_value)
        VALUES ('0189a1b2-c3d4-5e6f-7890-abcd12345678', 'BTCUSDT', true)
    """)

    # 等待通知
    await asyncio.sleep(0.1)

    assert len(notification_received) > 0
    assert notification_received[0]["event_type"] == "signal.new"
```

---

## 4. 端到端测试

### 4.1 测试范围

E2E 测试覆盖完整的业务流程：

| 业务流程 | 测试内容 |
|----------|----------|
| **K线更新→信号计算** | 完整事件链验证 |
| **信号写入→通知发送** | 数据持久化和通知触发 |
| **告警配置→策略执行** | 配置变更触发策略 |

### 4.2 完整事件链测试

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_kline_to_signal_event_chain():
    """测试 K线更新 → 信号计算 → 信号写入 → 通知发送 完整流程"""

    # 1. 模拟 K线数据更新
    kline_data = {
        "subscription_key": "BINANCE:BTCUSDT@KLINE_60",
        "data": {
            "k": {
                "o": "50000",
                "h": "51000",
                "l": "49000",
                "c": "50500",
                "v": "1000",
                "x": False  # 未闭合
            }
        },
        "is_closed": False
    }

    # 2. 更新 realtime_data 表
    await realtime_data_repo.update(kline_data)

    # 3. 验证 realtime.update 通知已发送
    notification = await wait_for_notification("realtime.update", timeout=5)
    assert notification["data"]["subscription_key"] == "BINANCE:BTCUSDT@KLINE_60"

    # 4. 信号服务处理通知并计算信号
    await signal_service.handle_realtime_update(notification)

    # 5. 验证信号已写入 strategy_signals 表
    signals = await signals_repo.get_by_symbol("BINANCE:BTCUSDT", limit=1)
    assert len(signals) > 0
    latest_signal = signals[0]

    # 6. 验证 signal.new 通知已发送
    signal_notification = await wait_for_notification("signal.new", timeout=5)
    assert signal_notification["data"]["id"] == latest_signal.id
```

### 4.3 告警配置变更事件链

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_alert_config_change_event_chain():
    """测试告警配置变更 → 信号服务响应 完整流程"""

    # 1. 创建告警配置
    alert_config = {
        "id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
        "name": "测试告警",
        "strategy_type": "macd_resonance_v5",
        "symbol": "BINANCE:BTCUSDT",
        "interval": "60",
        "trigger_type": "each_kline_close",
        "params": {
            "macd1_fastperiod": 12,
            "macd1_slowperiod": 26,
            "macd1_signalperiod": 9
        },
        "is_enabled": True
    }

    await alert_config_repo.insert(alert_config)

    # 2. 验证 alert_config.new 通知
    notification = await wait_for_notification("alert_config.new", timeout=5)
    assert notification["data"]["id"] == alert_config["id"]

    # 3. 信号服务应加载新的告警配置
    alert_signal = signal_service._alerts.get(
        UUID(alert_config["id"])
    )
    assert alert_signal is not None
    assert alert_signal.strategy_type == "macd_resonance_v5"

    # 4. 更新告警配置
    alert_config["params"]["macd1_fastperiod"] = 5
    await alert_config_repo.update(alert_config)

    # 5. 验证 alert_config.update 通知
    update_notification = await wait_for_notification("alert_config.update", timeout=5)

    # 6. 信号服务应更新策略实例
    updated_alert_signal = signal_service._alerts.get(
        UUID(alert_config["id"])
    )
    assert updated_alert_signal.params["macd1_fastperiod"] == 5

    # 7. 删除告警配置
    await alert_config_repo.delete(alert_config["id"])

    # 8. 验证 alert_config.delete 通知
    delete_notification = await wait_for_notification("alert_config.delete", timeout=5)

    # 9. 信号服务应移除告警实例
    removed_alert_signal = signal_service._alerts.get(
        UUID(alert_config["id"])
    )
    assert removed_alert_signal is None
```

---

## 5. 测试基础设施

### 5.1 测试数据库

每个服务使用独立的测试数据库：

```python
# conftest.py
import pytest
import asyncio
from databases import Database

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """测试数据库连接"""
    db = Database("postgresql://dbuser:pass@localhost:5432/trading_db_test")
    await db.connect()
    yield db
    await db.disconnect()

@pytest.fixture(autouse=True)
async def clean_test_data(test_db):
    """每个测试前清理数据"""
    yield
    # 清理测试数据
    await test_db.execute("DELETE FROM strategy_signals")
    await test_db.execute("DELETE FROM alert_configs")
```

### 5.2 测试夹具

```python
# fixtures.py
import pytest
from datetime import datetime

@pytest.fixture
def sample_kline_data():
    """示例K线数据"""
    return {
        "subscription_key": "BINANCE:BTCUSDT@KLINE_60",
        "data": {
            "k": {
                "o": "50000.00",
                "h": "51000.00",
                "l": "49000.00",
                "c": "50500.00",
                "v": "1234.56",
                "x": True,
                "t": 1704067200000
            }
        },
        "is_closed": True
    }

@pytest.fixture
def sample_alert_config():
    """示例告警配置"""
    return {
        "id": "0189a1b2-c3d4-5e6f-7890-abcd12345678",
        "name": "测试MACD共振告警",
        "strategy_type": "macd_resonance_v5",
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
        "is_enabled": True,
        "created_by": "test_user"
    }

@pytest.fixture
def mock_strategy():
    """模拟策略"""
    from unittest.mock import Mock

    strategy = Mock()
    strategy.calculate.return_value = Mock(signal_value=True)

    return strategy
```

### 5.3 测试标记

```python
# pytest.ini
[pytest]
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试
```

---

## 6. 测试运行

### 6.1 运行所有测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 运行 E2E 测试
pytest -m e2e
```

### 6.2 覆盖率报告

```bash
# 生成覆盖率报告
pytest --cov=src --cov-report=term-missing --cov-report=html

# 查看覆盖率
open htmlcov/index.html
```

### 6.3 持续集成

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: timescale/timescaledb:latest-pg16
        env:
          POSTGRES_USER: dbuser
          POSTGRES_PASSWORD: pass
          POSTGRES_DB: trading_db_test
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run unit tests
        run: pytest -m unit

      - name: Run integration tests
        run: pytest -m integration

      - name: Run E2E tests
        run: pytest -m e2e

      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

---

## 7. 信号服务测试策略

信号服务是系统的核心组件，需要重点测试。

### 7.1 单元测试

- **策略计算模块测试**：验证策略返回正确的信号值
- **数据筛选器测试**：验证按订阅键正确筛选数据
- **信号写入器测试**：验证信号正确写入数据库

### 7.2 集成测试

- **信号服务启动和订阅管理**：验证服务启动时正确初始化订阅
- **realtime.update 通知监听**：验证正确接收和处理实时数据更新
- **strategy_signals 表写入验证**：验证信号正确写入数据库
- **signal.new 通知触发验证**：验证信号写入后正确触发通知

### 7.3 E2E测试

- **完整事件链**：K线更新 → 信号计算 → 信号写入 → 通知发送

---

## 8. 相关文档

- [QUANT_TRADING_SYSTEM_ARCHITECTURE.md](./QUANT_TRADING_SYSTEM_ARCHITECTURE.md) - 完整实施文档
- [05-signal-service.md](./05-signal-service.md) - 信号服务设计
- [06-alert-service.md](./06-alert-service.md) - 告警服务设计

---

**版本**：v1.0
**更新**：2026-02-21
