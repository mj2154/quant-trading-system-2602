"""
pytest 配置和 Fixtures

统一管理：
- 路径自动配置
- WebSocket 连接 fixtures
- 测试标记定义
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Generator

import pytest

# ============================================================
# 路径自动配置
# ============================================================
def _setup_paths() -> None:
    """自动设置项目路径（只执行一次）"""
    # 避免重复添加
    existing_paths = set(sys.path)

    # api-service/src
    api_service_root = Path(__file__).parent.parent
    src_path = api_service_root / "src"
    if str(src_path) not in existing_paths:
        sys.path.insert(0, str(src_path))

    # 项目根目录 (shared模块)
    repo_root = Path("/home/ppadmin/code/quant-trading-system")
    if str(repo_root) not in existing_paths:
        sys.path.insert(0, str(repo_root))

    # binance-service (放在最后，避免覆盖 api-service 的 models)
    binance_service = repo_root / "services" / "binance-service" / "src"
    if str(binance_service) not in existing_paths:
        sys.path.append(str(binance_service))

# 执行路径设置
_setup_paths()

# ============================================================
# Pytest 配置
# ============================================================
def pytest_configure(config: pytest.Config) -> None:
    """注册测试标记"""
    config.addinivalue_line("markers", "spot: 现货市场测试")
    config.addinivalue_line("markers", "futures: 期货市场测试")
    config.addinivalue_line("markers", "rest: REST API测试")
    config.addinivalue_line("markers", "ws: WebSocket订阅测试")
    config.addinivalue_line("markers", "slow: 耗时较长的测试 (>10s)")
    config.addinivalue_line("markers", "realtime: 实时数据推送测试 (必须验证收到UPDATE消息)")


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建会话级别的事件循环（支持异步测试）"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def ws_uri() -> str:
    """WebSocket 连接 URI"""
    return "ws://localhost:8000/ws"


@pytest.fixture(scope="session")
def test_symbols() -> dict[str, list[str]]:
    """测试用的交易对"""
    return {
        "spot": ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"],
        "futures": ["BINANCE:BTCUSDT_PERP", "BINANCE:ETHUSDT_PERP"],
    }


@pytest.fixture(scope="session")
def kline_resolutions() -> list[str]:
    """支持的K线分辨率"""
    return ["1", "5", "15", "60", "240", "1D", "1W", "1M"]


# ============================================================
# 导入 e2e fixtures（从 tests/e2e/conftest.py）
# ============================================================
from tests.e2e.conftest import ws_client, ws_connected_client, ws_uri  # noqa: E402, F401
