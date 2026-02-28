"""
期货REST API测试 - 期货报价

测试用例: test_get_futures_quotes

验证:
1. 期货报价请求成功
2. 报价数据格式正确
3. 永续合约格式正确（.PERP后缀）

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


class TestFuturesQuotes(E2ETestBase):
    """期货报价数据测试"""

    def __init__(self):
        super().__init__()

    def _extract_quotes_data(self, response: dict) -> dict | None:
        """从响应中提取quotes数据

        服务端返回格式（异步任务结果）：
        {
            "action": "success",
            "data": {
                "type": "quotes",
                "quotes": [...],  // quotes 直接在 data 下（v2.1格式）
                "count": 2
            }
        }

        兼容旧格式（如果存在）：
        {
            "action": "success",
            "data": {
                "type": "quotes",
                "result": {
                    "count": 2,
                    "quotes": [...]
                }
            }
        }
        """
        data = response.get("data", {})

        # 优先尝试 v2.1 格式：quotes 直接在 data 下
        if "quotes" in data:
            return data

        # 回退旧格式：quotes 在 result 下
        result = data.get("result", {})
        if "quotes" in result:
            return result

        return None

    async def test_get_futures_quotes(self):
        """测试获取期货报价数据

        遵循设计文档的三阶段模式：
        1. 客户端发送请求（携带 requestId）
        2. 服务端返回 ack 确认（返回 requestId）
        3. 服务端异步处理完成后返回 success（返回 requestId 和数据）

        注意：get_quotes() 内部已经处理了 ack+success 两阶段响应，
        直接返回 success 响应，无需额外调用 wait_for_task_completion()
        """
        logger = self.logger
        logger.info("测试: 获取期货报价数据")

        # 测试永续合约报价
        # 注意：get_quotes() 内部已经处理了 ack+success 两阶段响应
        perpetual_quotes = ["BINANCE:BTCUSDT.PERP", "BINANCE:ETHUSDT.PERP"]
        response = await self.client.get_quotes(perpetual_quotes)

        # 步骤1: 验证响应（get_quotes 已返回 success）
        if not self.assert_response_success(response, "永续合约报价"):
            logger.error("永续合约报价失败")
            return False

        # get_quotes() 已返回 success 响应，无需再调用 wait_for_task_completion()
        # 直接使用 response 作为结果
        result = response

        # 步骤2: 提取并验证数据
        result_data = self._extract_quotes_data(result)
        if not result_data:
            logger.error("无法提取quotes数据")
            return False

        # 验证数据格式
        quotes = result_data.get("quotes", [])
        count = result_data.get("count", 0)

        if count != 2:
            logger.error("应该返回2个报价，实际: %d", count)
            return False

        if len(quotes) != 2:
            logger.error("quotes数组长度不匹配，实际: %d", len(quotes))
            return False

        # 验证报价字段 (遵循 TradingView API 规范)
        for quote in quotes:
            # TradingView 规范字段:
            # - n: 标的全名 (EXCHANGE:SYMBOL)
            # - s: 状态 (ok/error)
            # - v: 值对象 (包含 lp=last price, volume=成交量 等)

            # 验证符号是永续合约格式
            symbol = quote.get("n", "")
            if not symbol.endswith(".PERP"):
                logger.error("交易对应该是永续合约格式，实际: %s", symbol)
                return False

            # 验证状态
            status = quote.get("s", "")
            if status != "ok":
                logger.error("报价状态应该是 ok，实际: %s", status)
                return False

            # 验证价格字段 (在 v 对象内)
            v = quote.get("v", {})
            price = v.get("lp", 0)
            if price <= 0:
                logger.error("价格必须大于0，实际: %f", price)
                return False

            # 验证成交量 (在 v 对象内)
            volume = v.get("volume", 0)
            if volume < 0:
                logger.error("成交量必须大于等于0，实际: %f", volume)
                return False

            # 验证价格变化 (在 v 对象内)
            price_change = v.get("ch", 0)
            price_change_percent = v.get("chp", 0)

            logger.info(f"永续合约报价: {symbol} = {price}, 变化: {price_change_percent}%")

        logger.info("期货报价测试通过")
        return True


async def run_test():
    """独立运行此测试"""
    test = TestFuturesQuotes()
    try:
        async with test:
            await test.connect()
            result = await test.test_get_futures_quotes()
            return result
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
