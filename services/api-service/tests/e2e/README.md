# E2E测试重构说明

## 概述

将原有的4个聚合测试文件拆分为**21个独立测试文件**，每个测试都可以单独运行。

## 目录结构

```
tests/e2e/
├── __init__.py                    # 导出基类
├── base_e2e_test.py              # REST API测试基类
├── base_simple_test.py           # 简化WebSocket测试基类
├── utils/                        # 测试工具
│   ├── __init__.py
│   └── async_helpers.py         # 异步测试辅助函数
├── runners/                      # 测试运行器
│   ├── __init__.py
│   ├── spot_rest_runner.py      # 现货REST测试运行器
│   ├── spot_ws_runner.py        # 现货WebSocket测试运行器
│   ├── futures_rest_runner.py    # 期货REST测试运行器
│   ├── futures_ws_runner.py     # 期货WebSocket测试运行器
│   └── all_tests_runner.py       # 所有测试运行器
├── spot/                         # 现货测试
│   ├── __init__.py
│   └── rest/                     # 现货REST测试 (6个)
│       ├── __init__.py
│       ├── test_config.py        # test_get_config
│       ├── test_search_symbols.py # test_search_symbols
│       ├── test_klines.py        # test_get_spot_klines
│       ├── test_quotes.py        # test_get_spot_quotes
│       ├── test_multi_resolution.py # test_multi_resolution_klines
│       └── test_validation.py    # test_symbol_format_validation, test_time_range_validation
│   └── ws/                      # 现货WebSocket测试 (4个)
│       ├── __init__.py
│       ├── test_kline_sub.py     # test_kline_subscription
│       ├── test_quotes_sub.py    # test_quotes_subscription
│       ├── test_quotes_multi.py  # test_quotes_subscription_multi_symbol
│       └── test_multi_sub.py     # test_multi_subscription
└── futures/                      # 期货测试
    ├── __init__.py
    └── rest/                     # 期货REST测试 (7个)
        ├── __init__.py
        ├── test_perpetual_klines.py       # test_get_perpetual_klines
        ├── test_continuous_klines.py      # test_get_continuous_klines
        ├── test_futures_quotes.py         # test_get_futures_quotes
        ├── test_multi_resolution.py       # test_multi_resolution_futures_klines
        ├── test_symbol_validation.py      # test_futures_symbol_format_validation
        ├── test_price_logic.py            # test_futures_price_logic
        └── test_perpetual_spot_comparison.py # test_perpetual_vs_spot_comparison
    └── ws/                       # 期货WebSocket测试 (3个)
        ├── __init__.py
        ├── test_perpetual_kline_sub.py   # test_perpetual_kline
        ├── test_futures_quotes_sub.py    # test_futures_quotes
        └── test_multi_futures_sub.py     # test_multi_futures_subscription
```

## 测试统计

| 类型 | 测试数量 | 描述 |
|------|----------|------|
| 现货REST | 6 | 配置、搜索、K线、报价、分辨率、验证 |
| 现货WebSocket | 4 | K线订阅、报价订阅、多报价、多订阅 |
| 期货REST | 7 | 永续K线、连续K线、报价、分辨率、验证、价格逻辑、对比 |
| 期货WebSocket | 3 | 永续K线订阅、报价订阅、多期货订阅 |
| **总计** | **21** | |

## 运行方式

### 1. 运行单个测试文件

```bash
# 进入api-service目录
cd services/api-service

# 运行单个测试
uv run python tests/e2e/spot/rest/test_config.py
uv run python tests/e2e/spot/ws/test_kline_sub.py
uv run python tests/e2e/futures/rest/test_perpetual_klines.py
uv run python tests/e2e/futures/ws/test_perpetual_kline_sub.py
```

### 2. 使用pytest运行

```bash
# 运行单个测试
pytest tests/e2e/spot/rest/test_config.py -v
pytest tests/e2e/spot/ws/test_kline_sub.py -v

# 运行目录内所有测试
pytest tests/e2e/spot/rest/ -v
pytest tests/e2e/spot/ws/ -v
pytest tests/e2e/futures/rest/ -v
pytest tests/e2e/futures/ws/ -v

# 运行所有测试
pytest tests/e2e/ -v
```

### 3. 使用运行器

```bash
# 运行所有现货REST测试
python tests/e2e/runners/spot_rest_runner.py

# 运行所有现货WebSocket测试
python tests/e2e/runners/spot_ws_runner.py

# 运行所有期货REST测试
python tests/e2e/runners/futures_rest_runner.py

# 运行所有期货WebSocket测试
python tests/e2e/runners/futures_ws_runner.py

# 运行所有E2E测试
python tests/e2e/runners/all_tests_runner.py
```

## 适配异步任务机制

所有REST测试已适配最新的异步任务机制：

```python
async def _wait_for_async_result(
    self, response: dict, test_name: str, expected_type: str | None = None
) -> dict | None:
    """等待异步任务完成"""
    data = response.get("data", {})

    # 如果是同步响应，直接返回
    if data.get("type") in ["klines", "quotes", "config", "search_symbols"]:
        return data

    # 如果是任务创建响应，等待任务完成
    if data.get("type") == "task_created":
        task_id = data.get("taskId")
        result = await self.client.wait_for_task_completion(task_id, timeout=30)
        return result
```

## 每个测试文件的结构

每个独立测试文件都包含：

1. **测试类**: 继承自 `E2ETestBase` 或 `SimpleE2ETestBase`
2. **测试方法**: `test_*` 方法
3. **独立运行函数**: `run_test()` 函数
4. **main入口**: 支持命令行直接运行

```python
class TestSpotConfig(E2ETestBase):
    """现货交易所配置测试"""

    async def test_get_config(self):
        """测试获取交易所配置"""
        # 测试逻辑
        return True

async def run_test():
    """独立运行此测试"""
    test = TestSpotConfig()
    async with test:
        await test.connect()
        return await test.test_get_config()

if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
```

## 原测试文件

原有的4个测试文件保留在原位置（未修改）：

- `test_futures_rest_e2e.py` - 期货REST API测试
- `test_futures_ws_e2e.py` - 期货WebSocket测试
- `test_spot_rest_e2e.py` - 现货REST API测试
- `test_spot_ws_e2e.py` - 现货WebSocket测试

## 后续建议

1. **逐步迁移**: 可以逐步将新测试文件添加到CI/CD中
2. **并行测试**: 由于测试独立，可以并行运行不同类别的测试
3. **测试覆盖**: 确保所有21个测试都能通过
