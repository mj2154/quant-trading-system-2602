"""
测试配置

添加 src 目录到 Python 导入路径，使测试能够导入项目模块。
"""

import sys
from pathlib import Path

# 将 src 目录添加到 Python 导入路径
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 添加 shared 模块路径 (根目录，以便使用 shared.python.models 导入)
root_path = Path("/home/ppadmin/code/quant-trading-system")
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

# 添加 binance-service 模块路径 (放在最后，避免覆盖 api-service 的 models)
binance_service_path = Path("/home/ppadmin/code/quant-trading-system/services/binance-service/src")
if str(binance_service_path) not in sys.path:
    sys.path.append(str(binance_service_path))

import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
