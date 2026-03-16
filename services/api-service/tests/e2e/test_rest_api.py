"""
REST API 端到端测试（参数化）

使用 pytest.mark.parametrize 一套测试覆盖 spot/futures。
严格遵循 07-websocket-protocol.md 设计文档。

测试覆盖：
- GET_CONFIG: 获取配置
- GET_SEARCH_SYMBOLS: 搜索交易对
- GET_RESOLVE_SYMBOL: 解析交易对
- GET_KLINES: 获取K线数据
- GET_QUOTES: 获取报价数据
- GET_SERVER_TIME: 获取服务器时间
"""

import time

import pytest


class TestRestAPI:
    """REST API 端到端测试（参数化）"""

    # ========== 配置测试 ==========

    @pytest.mark.rest
    async def test_get_config(self, ws_connected_client):
        """测试 GET_CONFIG - 获取数据源配置

        设计文档: 07-websocket-protocol.md
        ConfigData 模型使用 camelCase 字段名
        """
        response = await ws_connected_client.get_config()

        assert response is not None, "无响应"
        assert response.get("type") == "CONFIG_DATA", f"期望 CONFIG_DATA，实际 {response.get('type')}"

        data = response.get("data", {})
        # 设计文档规定: supportedResolutions (camelCase)
        assert "supportedResolutions" in data, "缺少 supportedResolutions (设计文档规定)"
        assert data["supportedResolutions"], "supportedResolutions 为空"

    # ========== 交易对搜索测试 ==========

    @pytest.mark.rest
    @pytest.mark.parametrize("query", ["BTC", "ETH", ""])
    async def test_search_symbols(self, ws_connected_client, query):
        """测试 GET_SEARCH_SYMBOLS - 搜索交易对"""
        response = await ws_connected_client.search_symbols(query=query)

        assert response is not None, "无响应"
        assert response.get("type") == "SEARCH_SYMBOLS_DATA"

        data = response.get("data", {})
        assert "symbols" in data
        assert "total" in data

    # ========== 交易对解析测试 ==========

    @pytest.mark.rest
    @pytest.mark.parametrize("symbol,expected_ticker", [
        ("BINANCE:BTCUSDT", "BINANCE:BTCUSDT"),
        ("BINANCE:ETHUSDT", "BINANCE:ETHUSDT"),
        # PERP 解析后返回基础交易对
        ("BINANCE:BTCUSDT.PERP", "BINANCE:BTCUSDT"),
    ])
    async def test_resolve_symbol(self, ws_connected_client, symbol, expected_ticker):
        """测试 GET_RESOLVE_SYMBOL - 解析交易对"""
        response = await ws_connected_client.resolve_symbol(symbol=symbol)

        assert response is not None, "无响应"
        assert response.get("type") == "SYMBOL_DATA"

        data = response.get("data", {})
        # API返回ticker字段表示解析后的符号
        assert data.get("ticker") == expected_ticker

    # ========== K线数据测试 ==========

    @pytest.mark.rest
    @pytest.mark.parametrize("product_type,symbol,interval", [
        ("spot", "BINANCE:BTCUSDT", "1"),
        ("spot", "BINANCE:BTCUSDT", "5"),
        ("spot", "BINANCE:ETHUSDT", "1"),
        ("futures", "BINANCE:BTCUSDT.PERP", "1"),
        ("futures", "BINANCE:BTCUSDT.PERP", "5"),
        ("futures", "BINANCE:ETHUSDT.PERP", "1"),
    ])
    async def test_get_klines(self, ws_connected_client, product_type, symbol, interval):
        """测试 GET_KLINES - 获取K线数据"""
        now = int(time.time() * 1000)
        from_time = now - 3600 * 1000  # 1小时前
        to_time = now

        response = await ws_connected_client.get_klines(
            symbol=symbol,
            interval=interval,
            from_time=from_time,
            to_time=to_time,
        )

        assert response is not None, "无响应"
        assert response.get("type") == "KLINES_DATA", f"期望 KLINES_DATA，实际 {response.get('type')}"

        data = response.get("data", {})
        assert data.get("symbol") == symbol
        assert data.get("interval") == interval
        assert "bars" in data

    # ========== 报价数据测试 ==========

    @pytest.mark.rest
    @pytest.mark.parametrize("product_type,symbols", [
        ("spot", ["BINANCE:BTCUSDT"]),
        ("spot", ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"]),
        ("futures", ["BINANCE:BTCUSDT.PERP"]),
        ("futures", ["BINANCE:BTCUSDT.PERP", "BINANCE:ETHUSDT.PERP"]),
    ])
    async def test_get_quotes(self, ws_connected_client, product_type, symbols):
        """测试 GET_QUOTES - 获取报价数据"""
        response = await ws_connected_client.get_quotes(symbols=symbols)

        assert response is not None, "无响应"

        # 检查响应类型
        resp_type = response.get("type")
        assert resp_type in ["QUOTES_DATA", "ERROR"], f"意外的类型: {resp_type}"

        if resp_type == "QUOTES_DATA":
            data = response.get("data", {})
            assert "quotes" in data
            quotes = data["quotes"]
            assert len(quotes) == len(symbols), f"期望 {len(symbols)} 个报价，实际 {len(quotes)}"

            # 验证报价字段
            for quote in quotes:
                assert "n" in quote, "缺少标的名字段"
                assert "v" in quote, "缺少报价值字段"

                v = quote["v"]
                assert "lp" in v, "缺少最新价格字段"
                assert v["lp"] > 0, "最新价格应大于0"

    # ========== 服务器时间测试 ==========

    @pytest.mark.rest
    async def test_get_server_time(self, ws_connected_client):
        """测试 GET_SERVER_TIME - 获取服务器时间

        设计文档: 07-websocket-protocol.md
        ServerTimeData 使用 camelCase: serverTime
        """
        response = await ws_connected_client.get_server_time()

        assert response is not None, "无响应"
        assert response.get("type") == "SERVER_TIME_DATA"

        data = response.get("data", {})
        # 设计文档规定: serverTime (camelCase)
        assert "serverTime" in data, "缺少 serverTime (设计文档规定)"

        server_time = data["serverTime"]
        assert isinstance(server_time, int), "serverTime 应为整数"
        assert server_time > 1000000000000, "时间戳应该是毫秒级"


class TestConfig:
    """配置相关测试"""

    @pytest.mark.rest
    async def test_config_response_format(self, ws_connected_client):
        """验证配置响应格式

        设计文档: 07-websocket-protocol.md
        ConfigData 模型使用 camelCase 字段名
        """
        response = await ws_connected_client.get_config()

        # 验证协议格式
        assert response.get("protocolVersion") == "2.0"
        assert response.get("type") == "CONFIG_DATA"

        # 设计文档规定: 使用 camelCase 字段名
        data = response.get("data", {})
        required_fields = [
            "supportsSearch",
            "supportsGroupRequest",
            "supportsMarks",
            "supportsTime",
            "supportedResolutions",
            "currencyCodes",
        ]

        for field in required_fields:
            assert field in data, f"缺少必要字段: {field} (设计文档规定)"
