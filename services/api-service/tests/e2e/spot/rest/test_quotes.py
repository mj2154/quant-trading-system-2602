"""
现货REST API测试 - 获取报价数据

测试用例: test_get_spot_quotes

验证:
1. 单个报价请求和响应
2. 多个报价请求和响应
3. 报价数据格式正确
4. 价格和成交量字段有效

符合规范:
- TradingView-完整API规范设计文档.md (v2.1统一格式)
- 严格验证 type 字段在 data 内部
- 使用 assert_unified_response_format 验证响应格式
- 使用 assert_quotes_format 严格验证Quotes数据格式

作者: Claude Code
版本: v2.0.0
"""

import sys
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


class TestSpotQuotes(E2ETestBase):
    """现货报价数据测试"""

    def __init__(self):
        super().__init__(auto_connect=False)

    def _extract_quotes_data(self, response: dict) -> dict | None:
        """从响应中提取quotes数据

        根据TradingView API规范设计文档，Quotes响应格式：
        {
            "protocolVersion": "2.0",
            "action": "success",
            "requestId": "req_xxx",
            "timestamp": 1234567890,
            "data": {
                "type": "quotes",
                "quotes": [...]  // 直接在 data.quotes 下
            }
        }

        需要直接从 data 中提取 quotes 数据（v2.1统一格式）。
        """
        data = response.get("data", {})

        # 如果 data 中有 quotes，直接返回 data（包含quotes字段的对象）
        if "quotes" in data:
            return data
        return None

    async def test_get_spot_quotes(self):
        """测试获取现货报价数据

        遵循设计文档的三阶段模式：
        1. 客户端发送请求（携带 requestId）
        2. 服务端返回 ack 确认（返回 requestId）
        3. 服务端异步处理完成后返回 success（返回 requestId 和数据）

        严格遵循v2.1规范：
        - 使用 assert_unified_response_format 验证统一响应格式
        - type 字段必须在 data 内部
        - quotes 数据直接在 data 下，无需 result 包裹
        - 使用 assert_quotes_format 严格验证Quotes数据格式
        """
        logger = self.logger
        logger.info("测试: 获取现货报价数据")

        # 测试单个交易对
        # 注意：get_quotes() 内部已经处理了 ack+success 两阶段响应
        # 直接返回 success 响应，无需额外调用 wait_for_task_completion()
        logger.info("  测试: 单个报价")
        response = await self.client.get_quotes(["BINANCE:BTCUSDT"])

        if not self.assert_response_success(response, "获取单个报价"):
            logger.error("单个报价获取失败")
            return False

        # get_quotes() 已返回 success 响应，无需再调用 wait_for_task_completion()
        # 直接使用 response 作为结果
        result = response

        # 严格验证统一响应格式 (v2.1规范)
        if not self.assert_unified_response_format(result, "quotes"):
            logger.error("统一响应格式验证失败")
            return False

        # 提取 quotes 数据（v2.1格式：type在data内部，quotes直接在data下）
        data = result.get("data", {})
        quotes = data.get("quotes", [])

        if len(quotes) != 1:
            logger.error("应该返回1个报价，实际: %d", len(quotes))
            return False

        # 严格验证 quotes 数据格式
        if not self.assert_quotes_format(quotes, "单个报价"):
            logger.error("Quotes数据格式验证失败")
            return False

        # 验证报价字段内容
        quote = quotes[0]
        if quote.get("n") != "BINANCE:BTCUSDT":
            logger.error("交易对名称不匹配: %s", quote.get("n"))
            return False

        v = quote.get("v", {})
        if v.get("lp", 0) <= 0:
            logger.error("最新价格必须大于0")
            return False
        if v.get("volume", 0) <= 0:
            logger.error("成交量必须大于0")
            return False

        logger.info("  单个报价: %s, 成交量: %s", v.get("lp"), v.get("volume"))

        logger.info("所有现货报价测试通过")
        return True


async def run_test():
    """独立运行此测试"""
    test = TestSpotQuotes()
    try:
        async with test:
            await test.connect()
            result = await test.test_get_spot_quotes()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
