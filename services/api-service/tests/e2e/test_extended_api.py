"""
账户、订单、策略、信号查询 E2E 测试

严格遵循 07-websocket-protocol.md 设计文档。

测试覆盖：
- GET_FUTURES_ACCOUNT: 获取期货账户信息
- GET_SPOT_ACCOUNT: 获取现货账户信息
- GET_OPEN_ORDERS: 查询当前挂单
- LIST_ORDERS: 查询订单列表
- GET_STRATEGY_METADATA: 获取策略元数据列表
- GET_STRATEGY_METADATA_BY_TYPE: 获取指定策略元数据
- LIST_SIGNALS: 查询历史信号
- GET_METRICS: 获取服务指标

注意：测试严格验证设计文档规定的格式，不适配实际实现。
如果测试失败，说明后端实现与设计文档不一致，需要修复。
"""

import pytest


class TestAccountAPI:
    """账户查询测试

    注意：账户信息采用透传模式，data.account 包含 Binance API 返回的原始数据。
    具体字段取决于 Binance API 返回的实际数据格式，测试只需验证基本结构。
    """

    @pytest.mark.ws
    async def test_get_futures_account_response_format(self, ws_connected_client):
        """测试 GET_FUTURES_ACCOUNT 响应格式

        设计文档: 07-websocket-protocol.md
        响应类型: ACCOUNT_DATA

        设计文档规定格式（透传模式）:
        {
            "type": "ACCOUNT_DATA",
            "data": {
                "account": {
                    // 透传 Binance API 返回的完整 JSON 数据
                }
            }
        }
        """
        response = await ws_connected_client.get_futures_account()

        # 验证顶层字段
        assert "protocolVersion" in response, "缺少 protocolVersion 字段"
        assert response["protocolVersion"] == "2.0"

        assert "type" in response, "缺少 type 字段"
        assert response["type"] == "ACCOUNT_DATA", \
            f"type 应为 ACCOUNT_DATA，实际为 {response['type']}"

        assert "requestId" in response, "缺少 requestId 字段"
        assert "timestamp" in response, "缺少 timestamp 字段"

        # 验证 data.account 字段（透传模式：包含 Binance API 返回的原始数据）
        assert "data" in response, "缺少 data 字段"
        data = response["data"]
        assert "account" in data, \
            f"data.account 字段不存在，实际 data 包含: {list(data.keys())}"

        account = data["account"]
        # 透传模式下，account 是 Binance API 返回的原始数据，只需验证不为空
        assert account is not None and len(account) > 0, \
            f"account 字段不应为空"

        print(f"[DEBUG] 期货账户响应符合设计文档（透传模式）: account 包含 {len(account)} 个字段")

    @pytest.mark.ws
    async def test_get_spot_account_response_format(self, ws_connected_client):
        """测试 GET_SPOT_ACCOUNT 响应格式

        设计文档: 07-websocket-protocol.md
        响应类型: ACCOUNT_DATA

        设计文档规定格式（透传模式）:
        {
            "type": "ACCOUNT_DATA",
            "data": {
                "account": {
                    // 透传 Binance API 返回的完整 JSON 数据
                }
            }
        }
        """
        response = await ws_connected_client.get_spot_account()

        # 验证顶层字段
        assert "protocolVersion" in response, "缺少 protocolVersion 字段"
        assert response["protocolVersion"] == "2.0"

        assert "type" in response, "缺少 type 字段"
        assert response["type"] == "ACCOUNT_DATA", \
            f"type 应为 ACCOUNT_DATA，实际为 {response['type']}"

        assert "requestId" in response, "缺少 requestId 字段"
        assert "timestamp" in response, "缺少 timestamp 字段"

        # 验证 data.account 字段（透传模式）
        assert "data" in response, "缺少 data 字段"
        data = response["data"]
        assert "account" in data, \
            f"data.account 字段不存在，实际 data 包含: {list(data.keys())}"

        account = data["account"]
        # 透传模式下，account 是 Binance API 返回的原始数据，只需验证不为空
        assert account is not None and len(account) > 0, \
            f"account 字段不应为空"

        print(f"[DEBUG] 现货账户响应符合设计文档（透传模式）: account 包含 {len(account)} 个字段")


class TestOrderAPI:
    """订单查询测试"""

    @pytest.mark.ws
    async def test_get_open_orders_response_format(self, ws_connected_client):
        """测试 GET_OPEN_ORDERS 响应格式

        设计文档: 07-websocket-protocol.md
        响应类型: ORDER_LIST_DATA

        设计文档规定格式:
        {
            "type": "ORDER_LIST_DATA",
            "data": {
                "orders": [...],
                "count": N
            }
        }
        """
        response = await ws_connected_client.get_open_orders()

        # 验证响应类型
        assert response.get("type") == "ORDER_LIST_DATA", \
            f"type 应为 ORDER_LIST_DATA，实际为 {response.get('type')}"

        # 验证 data 字段
        data = response.get("data", {})
        assert "orders" in data, "data.orders 字段不存在"
        assert isinstance(data["orders"], list), "data.orders 应为数组"
        assert "count" in data, "data.count 字段不存在"

        print(f"[DEBUG] 当前挂单响应符合设计文档: {response}")

    @pytest.mark.ws
    async def test_list_orders_response_format(self, ws_connected_client):
        """测试 LIST_ORDERS 响应格式

        设计文档: 07-websocket-protocol.md
        响应类型: ORDER_LIST_DATA

        设计文档规定格式:
        {
            "type": "ORDER_LIST_DATA",
            "data": {
                "orders": [...],
                "count": N
            }
        }
        """
        # 使用正确的交易对格式（期货）
        response = await ws_connected_client.list_orders(symbol="BTCUSDT.PERP")

        # 验证响应类型
        assert response.get("type") == "ORDER_LIST_DATA", \
            f"type 应为 ORDER_LIST_DATA，实际为 {response.get('type')}"

        # 验证 data 字段
        data = response.get("data", {})
        assert "orders" in data, "data.orders 字段不存在"
        assert isinstance(data["orders"], list), "data.orders 应为数组"
        assert "count" in data, "data.count 字段不存在"

        print(f"[DEBUG] 订单列表响应符合设计文档: {response}")


class TestStrategyMetadataAPI:
    """策略元数据测试"""

    @pytest.mark.ws
    async def test_get_strategy_metadata_response_format(self, ws_connected_client):
        """测试 GET_STRATEGY_METADATA 响应格式

        设计文档: 07-websocket-protocol.md
        响应类型: STRATEGY_METADATA_DATA

        设计文档规定格式:
        {
            "type": "STRATEGY_METADATA_DATA",
            "data": {
                "strategies": [
                    {
                        "type": "MACDResonanceStrategyV5",
                        "name": "MACD共振策略V5",
                        "description": "...",
                        "params": [...]
                    }
                ]
            }
        }
        """
        response = await ws_connected_client.get_strategy_metadata()

        # 验证响应类型
        assert response.get("type") == "STRATEGY_METADATA_DATA", \
            f"type 应为 STRATEGY_METADATA_DATA，实际为 {response.get('type')}"

        # 验证 data.strategies 字段
        data = response.get("data", {})
        assert "strategies" in data, "data.strategies 字段不存在"
        assert isinstance(data["strategies"], list), "data.strategies 应为数组"

        # 验证策略格式
        if len(data["strategies"]) > 0:
            strategy = data["strategies"][0]
            assert "type" in strategy, "策略缺少 type 字段"
            assert "name" in strategy, "策略缺少 name 字段"
            assert "description" in strategy, "策略缺少 description 字段"
            assert "params" in strategy, "策略缺少 params 字段"
            assert isinstance(strategy["params"], list), "params 应为数组"

            # 验证参数格式
            if len(strategy["params"]) > 0:
                param = strategy["params"][0]
                assert "name" in param, "参数缺少 name 字段"
                assert "type" in param, "参数缺少 type 字段"
                assert "default" in param, "参数缺少 default 字段"

        print(f"[DEBUG] 策略元数据响应符合设计文档: {response}")

    @pytest.mark.ws
    async def test_get_strategy_metadata_by_type_response_format(self, ws_connected_client):
        """测试 GET_STRATEGY_METADATA_BY_TYPE 响应格式

        设计文档: 07-websocket-protocol.md
        响应类型: STRATEGY_METADATA_DATA

        设计文档规定格式:
        {
            "type": "STRATEGY_METADATA_DATA",
            "data": {
                "strategy": {
                    "type": "MACDResonanceStrategyV5",
                    "name": "...",
                    "description": "...",
                    "params": [...]
                }
            }
        }
        """
        # 先获取所有策略
        all_response = await ws_connected_client.get_strategy_metadata()
        strategies = all_response.get("data", {}).get("strategies", [])

        if len(strategies) == 0:
            pytest.skip("没有可用的策略元数据")

        # 使用第一个策略的 type 进行测试
        first_strategy_type = strategies[0]["type"]

        response = await ws_connected_client.get_strategy_metadata_by_type(first_strategy_type)

        # 验证响应类型
        assert response.get("type") == "STRATEGY_METADATA_DATA", \
            f"type 应为 STRATEGY_METADATA_DATA，实际为 {response.get('type')}"

        # 验证 data.strategy 字段
        data = response.get("data", {})
        assert "strategy" in data, "data.strategy 字段不存在"

        strategy = data["strategy"]
        assert strategy["type"] == first_strategy_type, \
            f"返回的策略 type 应为 {first_strategy_type}，实际为 {strategy['type']}"
        assert "name" in strategy, "策略缺少 name 字段"
        assert "description" in strategy, "策略缺少 description 字段"
        assert "params" in strategy, "策略缺少 params 字段"

        print(f"[DEBUG] 指定策略元数据响应符合设计文档: {response}")


class TestSignalsAPI:
    """信号查询测试"""

    @pytest.mark.ws
    async def test_list_signals_response_format(self, ws_connected_client):
        """测试 LIST_SIGNALS 响应格式

        设计文档: 07-websocket-protocol.md
        响应类型: SIGNAL_DATA

        设计文档规定格式:
        {
            "type": "SIGNAL_DATA",
            "data": {
                "items": [...],
                "total": N,
                "page": N,
                "pageSize": N
            }
        }
        """
        response = await ws_connected_client.list_signals(
            page=1,
            page_size=20,
            symbol="BINANCE:BTCUSDT"
        )

        # 验证响应类型
        assert response.get("type") == "SIGNAL_DATA", \
            f"type 应为 SIGNAL_DATA，实际为 {response.get('type')}"

        # 验证 data 字段
        data = response.get("data", {})
        assert "items" in data, "data.items 字段不存在"
        assert isinstance(data["items"], list), "data.items 应为数组"
        assert "total" in data, "data.total 字段不存在"
        assert "page" in data, "data.page 字段不存在"
        assert "pageSize" in data, "data.pageSize 字段不存在"

        # 验证信号格式（如果有数据）
        if len(data["items"]) > 0:
            signal = data["items"][0]
            required_fields = ["id", "symbol", "interval", "signalValue", "computedAt"]
            for field in required_fields:
                assert field in signal, f"信号缺少必要字段: {field}"

        print(f"[DEBUG] 信号列表响应符合设计文档: {response}")


class TestMetricsAPI:
    """服务指标测试"""

    @pytest.mark.ws
    async def test_get_metrics_response_format(self, ws_connected_client):
        """测试 GET_METRICS 响应格式

        设计文档: 07-websocket-protocol.md
        响应类型: METRICS_DATA

        设计文档规定格式:
        {
            "type": "METRICS_DATA",
            "data": {...}
        }
        """
        response = await ws_connected_client.get_metrics()

        # 验证响应类型
        assert response.get("type") == "METRICS_DATA", \
            f"type 应为 METRICS_DATA，实际为 {response.get('type')}"

        # 验证 data 字段存在且为对象
        assert "data" in response, "缺少 data 字段"
        assert isinstance(response["data"], dict), "data 应为对象"

        # 验证至少有部分指标数据
        data = response["data"]
        assert len(data) > 0, "指标数据不应为空"

        print(f"[DEBUG] 服务指标响应符合设计文档: {response}")
