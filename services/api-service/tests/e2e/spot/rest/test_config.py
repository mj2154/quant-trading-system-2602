"""
现货REST API测试 - 获取交易所配置

测试用例: test_get_config

验证:
1. 配置请求成功响应
2. 配置包含所有必要字段
3. 支持的分辨率正确
4. 货币代码包含USDT

符合规范:
- TradingView-完整API规范设计文档.md (v2.1统一格式)
- 严格验证 type 字段在 data 内部
- 使用 assert_unified_response_format 验证响应格式

作者: Claude Code
版本: v2.0.0
"""

import sys
from pathlib import Path

# 添加路径支持
_current = Path(__file__).resolve()
_api_service_root = _current.parent.parent.parent.parent  # spot/rest/ -> tests/e2e/ -> api-service/
_src_path = _api_service_root / "src"
_tests_path = _api_service_root / "tests"

for p in [_src_path, _tests_path]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import asyncio
from typing import Any

from tests.e2e.base_e2e_test import E2ETestBase


class TestSpotConfig(E2ETestBase):
    """现货交易所配置测试"""

    def __init__(self):
        super().__init__(auto_connect=False)

    async def test_get_config(self):
        """测试获取交易所配置

        严格遵循v2.1规范：
        - 使用 assert_unified_response_format 验证统一响应格式
        - type 字段必须在 data 内部
        - 验证所有配置字段符合TradingView规范
        """
        logger = self.logger
        logger.info("测试: 获取交易所配置")

        # 发送GET config请求
        response = await self.client.get_config()

        # 验证响应
        assert self.assert_response_success(response, "获取配置"), "配置获取失败"

        # 严格验证统一响应格式 (v2.1规范)
        assert self.assert_unified_response_format(response, "config"), "统一响应格式验证失败"

        # 验证配置内容
        data = response.get("data", {})
        assert "supported_resolutions" in data, "缺少supported_resolutions"
        assert "currency_codes" in data, "缺少currency_codes"
        assert "symbols_types" in data, "缺少symbols_types"

        # 验证支持的分辨率
        supported_resolutions = data.get("supported_resolutions", [])
        expected_resolutions = ["1", "5", "15", "60", "240", "1D", "1W", "1M"]
        for res in expected_resolutions:
            assert res in supported_resolutions, f"不支持的分辨率: {res}"

        # 验证货币代码
        currency_codes = data.get("currency_codes", [])
        assert "USDT" in currency_codes, "缺少USDT"

        logger.info("配置获取成功: 支持%d种分辨率", len(supported_resolutions))
        return True


async def run_test():
    """独立运行此测试"""
    test = TestSpotConfig()
    try:
        async with test:
            await test.connect()
            result = await test.test_get_config()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
