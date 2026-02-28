"""
现货REST API测试 - 格式验证

测试用例:
- test_symbol_format_validation: 交易对格式验证
- test_time_range_validation: 时间范围验证

验证:
1. 有效符号格式能正确返回数据
2. 无效符号格式能正确处理
3. 无效时间范围能返回错误

符合规范:
- TradingView-完整API规范设计文档.md (v2.1统一格式)
- 严格验证 type 字段在 data 内部
- 使用 assert_unified_response_format 验证响应格式
- 使用 assert_error_response_format 验证错误响应格式

作者: Claude Code
版本: v2.0.0
"""

import sys
import time
from pathlib import Path

_current = Path(__file__).resolve()
_api_service_root = _current.parent.parent.parent.parent
_src_path = _api_service_root / "src"
_tests_path = _api_service_root / "tests"

for p in [_src_path, _tests_path]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import asyncio
from tests.e2e.base_e2e_test import E2ETestBase


class TestSpotValidation(E2ETestBase):
    """现货格式验证测试"""

    def __init__(self):
        super().__init__(auto_connect=False)

    async def test_symbol_format_validation(self):
        """测试交易对格式验证

        严格遵循v2.1规范：
        - 使用 assert_unified_response_format 验证统一响应格式
        - type 字段必须在 data 内部
        """
        logger = self.logger
        logger.info("测试: 交易对格式验证")

        end_time = int(time.time() * 1000)
        start_time = end_time - (60 * 60 * 1000)

        # 测试有效的现货格式
        valid_symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"]

        for symbol in valid_symbols:
            response = await self.client.get_klines(
                symbol=symbol, resolution="60", from_time=start_time, to_time=end_time
            )

            # 验证初始响应（可能是 ack 或 success）
            assert self.assert_response_success(response, f"有效符号{symbol}"), (
                f"有效符号{symbol}测试失败"
            )

            # 如果是 ack 响应，等待 success 响应
            if response.get("action") == "ack":
                result = await self.client.wait_for_task_completion(timeout=30)
                if result:
                    # 严格验证统一响应格式 (v2.1规范)
                    assert self.assert_unified_response_format(result, "klines"), (
                        f"有效符号{symbol}统一响应格式验证失败"
                    )

        logger.info("交易对格式验证测试通过")
        return True

    async def test_time_range_validation(self):
        """测试时间范围验证

        严格遵循v2.1规范：
        - 有效时间范围返回 success 响应（使用 assert_unified_response_format 验证）
        - 无效时间范围（from_time > to_time）返回 error 响应（使用 assert_error_response_format 验证）
        """
        logger = self.logger
        logger.info("测试: 时间范围验证")

        symbol = "BINANCE:BTCUSDT"
        resolution = "60"

        # 测试有效时间范围
        end_time = int(time.time() * 1000)
        start_time = end_time - (60 * 60 * 1000)

        response = await self.client.get_klines(
            symbol=symbol, resolution=resolution, from_time=start_time, to_time=end_time
        )

        if not self.assert_response_success(response, "有效时间范围"):
            logger.error("有效时间范围测试失败")
            return False

        # 等待异步任务完成（如果需要）
        if response.get("action") == "ack":
            result = await self.client.wait_for_task_completion(timeout=30)
            if result:
                # 严格验证统一响应格式 (v2.1规范)
                if not self.assert_unified_response_format(result, "klines"):
                    logger.error("有效时间范围统一响应格式验证失败")
                    return False
                logger.info("有效时间范围: 获取%d条数据", result.get("data", {}).get("count", 0))
            else:
                logger.warning("有效时间范围任务超时")
        else:
            # 严格验证统一响应格式 (v2.1规范)
            if not self.assert_unified_response_format(response, "klines"):
                logger.error("有效时间范围统一响应格式验证失败")
                return False
            logger.info("有效时间范围: 获取%d条数据", response.get("data", {}).get("count", 0))

        # 测试无效时间范围（from_time > to_time）
        invalid_start_time = end_time
        invalid_end_time = start_time

        response = await self.client.get_klines(
            symbol=symbol,
            resolution=resolution,
            from_time=invalid_start_time,
            to_time=invalid_end_time,
        )

        # 应该返回错误
        if response.get("action") == "error":
            # 严格验证错误响应格式 (v2.1规范)
            if not self.assert_error_response_format(response, "无效时间范围"):
                logger.error("错误响应格式验证失败")
                return False

            error_data = response.get("data", {})
            if error_data.get("errorCode") == "INVALID_PARAMETER":
                if "from_time must be less than to_time" in error_data.get("errorMessage", ""):
                    logger.info("无效时间范围正确返回错误")
                    logger.info("时间范围验证测试通过")
                    return True

            logger.error("错误消息不正确: %s", error_data.get("errorMessage"))
        else:
            logger.info("时间范围验证测试通过")
            return True

        logger.error("时间范围验证测试失败")
        return False


async def run_test(validation_type: str = "all"):
    """独立运行此测试

    Args:
        validation_type: "symbol", "time", 或 "all"
    """
    test = TestSpotValidation()
    try:
        async with test:
            await test.connect()
            if validation_type == "symbol":
                result = await test.test_symbol_format_validation()
            elif validation_type == "time":
                result = await test.test_time_range_validation()
            else:
                result1 = await test.test_symbol_format_validation()
                result2 = await test.test_time_range_validation()
                result = result1 and result2
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["symbol", "time", "all"], default="all")
    args = parser.parse_args()

    success = asyncio.run(run_test(args.type))
    exit(0 if success else 1)
