"""
异步测试辅助函数

提供异步测试的工具函数:
- async_test: 装饰器，用于标记异步测试
- run_async_test: 运行异步测试的辅助函数
- timeout_checker: 超时检查器

作者: Claude Code
版本: v2.0.0
"""

import asyncio
import functools
import sys
from pathlib import Path
from typing import Any, Callable


def async_test(func: Callable) -> Callable:
    """装饰器：标记函数为异步测试函数"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def run_async_test(coro: asyncio.coroutine) -> Any:
    """运行异步协程"""
    return asyncio.run(coro)


class timeout_checker:
    """超时检查器"""

    def __init__(self, timeout: float = 30.0):
        """初始化超时检查器

        Args:
            timeout: 超时时间（秒）
        """
        self.timeout = timeout
        self.start_time = None

    async def __aenter__(self):
        """进入上下文时记录开始时间"""
        self.start_time = asyncio.get_event_loop().time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时检查是否超时"""
        elapsed = asyncio.get_event_loop().time() - self.start_time
        if elapsed > self.timeout:
            raise TimeoutError(f"操作超时: {elapsed:.2f}s > {self.timeout}s")
        return False

    @staticmethod
    async def check(timeout: float = 30.0) -> bool:
        """检查是否超时"""
        await asyncio.sleep(0)
        return True


def create_test_client(base_url: str = "ws://localhost:8000/ws/market") -> dict:
    """创建测试客户端配置

    Args:
        base_url: WebSocket服务器地址

    Returns:
        客户端配置字典
    """
    return {
        "base_url": base_url,
        "timeout": 10.0,
        "reconnect_attempts": 3,
        "reconnect_delay": 1.0,
    }


def format_test_result(result: dict) -> str:
    """格式化测试结果

    Args:
        result: 测试结果字典

    Returns:
        格式化的结果字符串
    """
    passed = result.get("passed", 0)
    failed = result.get("failed", 0)
    total = passed + failed

    if failed == 0:
        return f"✅ {total}/{total} 通过"
    else:
        errors = result.get("errors", [])
        error_lines = "\n".join(f"  ❌ {e}" for e in errors[:5])
        return f"⚠️ {passed}/{total} 通过, {failed} 失败\n{error_lines}"


if __name__ == "__main__":
    # 简单测试
    async def test_example():
        async with timeout_checker(5.0) as checker:
            await asyncio.sleep(0.1)
            print("测试通过!")

    asyncio.run(test_example())
