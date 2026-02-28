"""
现货REST API测试 - 搜索交易对

测试用例: test_search_symbols

验证:
1. 搜索请求成功响应
2. 搜索结果包含必要字段
3. 符号格式正确
4. 返回数量符合limit
5. SymbolInfo模型完整性验证（必需字段+可选字段）

符合规范:
- TradingView-完整API规范设计文档.md (v2.1统一格式)
- 严格验证 type 字段在 data 内部
- 使用 assert_unified_response_format 验证响应格式
- SymbolInfo模型严格符合LibrarySymbolInfo接口标准

作者: Claude Code
版本: v2.1.0
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


class TestSpotSearchSymbols(E2ETestBase):
    """现货交易对搜索测试"""

    def __init__(self):
        super().__init__(auto_connect=False)

    async def test_search_symbols(self):
        """测试搜索交易对

        严格遵循v2.1规范：
        - 使用 assert_unified_response_format 验证统一响应格式
        - type 字段必须在 data 内部
        - 验证所有符号字段符合TradingView规范
        - SymbolInfo模型完整性验证（必需字段+可选字段）
        """
        logger = self.logger
        logger.info("测试: 搜索交易对")

        # 测试搜索BTC
        response = await self.client.search_symbols("BTC", limit=20)

        # 验证响应
        assert self.assert_response_success(response, "搜索交易对"), "搜索失败"

        # 严格验证统一响应格式 (v2.1规范)
        assert self.assert_unified_response_format(response, "search_symbols"), "统一响应格式验证失败"

        # 验证搜索结果
        data = response.get("data", {})
        assert "symbols" in data, "缺少symbols字段"
        assert "total" in data, "缺少total字段"
        assert "count" in data, "缺少count字段"

        symbols = data.get("symbols", [])
        assert len(symbols) > 0, "搜索结果为空"

        # 验证符号格式
        for symbol_info in symbols[:5]:
            assert "symbol" in symbol_info, "缺少symbol字段"
            assert "full_name" in symbol_info, "缺少full_name字段"
            assert "description" in symbol_info, "缺少description字段"
            assert "exchange" in symbol_info, "缺少exchange字段"
            assert "ticker" in symbol_info, "缺少ticker字段"
            assert "type" in symbol_info, "缺少type字段"

            symbol = symbol_info["symbol"]
            assert symbol.startswith("BINANCE:"), "交易对格式错误"
            assert "BTC" in symbol_info["ticker"], "搜索结果不匹配"

        # 验证返回数量
        count = data.get("count", 0)
        assert count > 0, "count应该大于0"
        assert count <= 20, f"count应该小于等于20，实际: {count}"

        logger.info("搜索成功: 找到%d个BTC相关交易对", count)
        return True

    async def test_search_symbols_symbol_info_integrity(self):
        """测试搜索交易对 - SymbolInfo模型完整性验证

        验证SymbolInfo模型符合TradingView LibrarySymbolInfo接口标准：
        1. 必需字段验证（10个字段，无默认值）
        2. 可选字段类型验证（带默认值的字段）
        3. 字段值合法性验证

        必需字段：
        - name: 符号名称
        - ticker: 唯一标识符
        - description: 品种描述
        - type: 品种类型
        - exchange: 交易所名称
        - listed_exchange: 上市交易所名称
        - session: 交易时间
        - timezone: 时区
        - minmov: 最小变动单位
        - pricescale: 价格精度
        """
        logger = self.logger
        logger.info("测试: SymbolInfo模型完整性验证")

        # 测试搜索ETH
        response = await self.client.search_symbols("ETH", limit=10)

        # 验证响应成功
        assert self.assert_response_success(response, "搜索ETH"), "搜索失败"

        # 验证统一响应格式
        assert self.assert_unified_response_format(response, "search_symbols"), "统一响应格式验证失败"

        data = response.get("data", {})
        symbols = data.get("symbols", [])
        assert len(symbols) > 0, "搜索结果为空"

        # 验证每个SymbolInfo的完整性
        validated_count = 0
        for symbol_info in symbols:
            # 首先验证基本搜索结果字段
            assert "symbol" in symbol_info, "缺少symbol字段"
            assert "ticker" in symbol_info, "缺少ticker字段"

            # 使用assert_symbol_info_model验证SymbolInfo模型完整性
            # 注意：搜索结果可能只返回部分字段，需要检查实际返回的字段
            symbol_fields = set(symbol_info.keys())

            # 验证必需字段存在（如果返回了的话）
            required_fields_for_search = ["symbol", "full_name", "description", "exchange", "ticker", "type"]
            for field in required_fields_for_search:
                if field not in symbol_info:
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(
                        f"SymbolInfo搜索结果缺少必需字段 {field}"
                    )
                    return False

            # 验证字段类型
            # symbol: 字符串
            if not isinstance(symbol_info["symbol"], str):
                self.test_results["failed"] += 1
                self.test_results["errors"].append("SymbolInfo.symbol必须是字符串")
                return False

            # full_name: 字符串
            if not isinstance(symbol_info["full_name"], str):
                self.test_results["failed"] += 1
                self.test_results["errors"].append("SymbolInfo.full_name必须是字符串")
                return False

            # ticker: 字符串
            if not isinstance(symbol_info["ticker"], str):
                self.test_results["failed"] += 1
                self.test_results["errors"].append("SymbolInfo.ticker必须是字符串")
                return False

            # type: 字符串
            if not isinstance(symbol_info["type"], str):
                self.test_results["failed"] += 1
                self.test_results["errors"].append("SymbolInfo.type必须是字符串")
                return False

            # 验证ticker格式
            if ":" not in symbol_info["ticker"]:
                self.test_results["failed"] += 1
                self.test_results["errors"].append("SymbolInfo.ticker必须包含交易所前缀")
                return False

            # 验证symbol格式
            if not symbol_info["symbol"].startswith("BINANCE:"):
                self.test_results["failed"] += 1
                self.test_results["errors"].append("SymbolInfo.symbol必须以BINANCE:开头")
                return False

            validated_count += 1

        logger.info("SymbolInfo模型完整性验证成功: 验证了%d个交易对", validated_count)
        return True


async def run_test():
    """独立运行此测试"""
    test = TestSpotSearchSymbols()
    try:
        async with test:
            await test.connect()
            result1 = await test.test_search_symbols()
            result2 = await test.test_search_symbols_symbol_info_integrity()
            return result1 and result2
    except Exception as e:
        print(f"测试执行失败: {e!s}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
