"""
策略配置和信号查询 API 测试

测试 REST API 端点的功能和正确性。
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any
from fastapi.testclient import TestClient


class MockConfigRecord:
    """模拟策略配置记录"""

    def __init__(
        self,
        id: UUID | None = None,
        name: str = "test_strategy",
        description: str | None = None,
        trigger_type: str = "each_kline_close",
        macd_params: dict[str, Any] | None = None,
        threshold: float = 0.0,
        symbol: str = "BINANCE:BTCUSDT",
        interval: str = "60",
        is_enabled: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        created_by: str | None = None,
    ):
        self.id = id or uuid4()
        self.name = name
        self.description = description
        self.trigger_type = trigger_type
        self.macd_params = macd_params or {}
        self.threshold = threshold
        self.symbol = symbol
        self.interval = interval
        self.is_enabled = is_enabled
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.created_by = created_by


class MockSignalRecord:
    """模拟信号记录"""

    def __init__(
        self,
        id: int = 1,
        signal_id: UUID | None = None,
        config_id: UUID | None = None,
        strategy_name: str = "test_strategy",
        symbol: str = "BINANCE:BTCUSDT",
        interval: str = "60",
        trigger_type: str | None = "each_kline_close",
        signal_value: bool | None = True,
        signal_reason: str | None = "MACD crossover",
        computed_at: datetime | None = None,
        source_subscription_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = id
        self.signal_id = signal_id or uuid4()
        self.config_id = config_id
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.interval = interval
        self.trigger_type = trigger_type
        self.signal_value = signal_value
        self.signal_reason = signal_reason
        self.computed_at = computed_at or datetime.now()
        self.source_subscription_key = source_subscription_key
        self.metadata = metadata or {}


def create_mock_config_repo():
    """创建模拟的策略配置仓储"""
    mock_repo = AsyncMock()

    # 预置测试数据
    test_config_id = uuid4()
    test_config_dict = {
        "id": test_config_id,
        "name": "test_strategy",
        "description": "Test strategy description",
        "trigger_type": "each_kline_close",
        "macd_params": {"fast1": 12, "slow1": 26, "signal1": 9},
        "threshold": 0.0,
        "symbol": "BINANCE:BTCUSDT",
        "interval": "60",
        "is_enabled": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "created_by": "test_user",
    }

    # mock find_all - 返回字典列表（与真实仓储一致）
    mock_repo.find_all = AsyncMock(return_value=([test_config_dict], 1))

    # mock create
    mock_repo.create = AsyncMock(return_value=test_config_id)

    # mock find_by_id
    mock_repo.find_by_id = AsyncMock(return_value=test_config_dict)

    # mock update
    mock_repo.update = AsyncMock(return_value=True)

    # mock delete
    mock_repo.delete = AsyncMock(return_value=True)

    # mock enable/disable
    mock_repo.enable = AsyncMock(return_value=True)
    mock_repo.disable = AsyncMock(return_value=True)

    return mock_repo, test_config_id, test_config_dict


def create_mock_signal_repo():
    """创建模拟的信号仓储"""
    mock_repo = AsyncMock()

    # 预置测试数据
    test_signal = MockSignalRecord(
        id=1,
        signal_id=uuid4(),
        config_id=uuid4(),
        strategy_name="test_strategy",
        symbol="BINANCE:BTCUSDT",
        interval="60",
    )

    # mock find_all
    mock_repo.find_all = AsyncMock(return_value=([test_signal], 1))

    # mock find_by_id
    mock_repo.find_by_id = AsyncMock(return_value=test_signal)

    # mock find_recent
    mock_repo.find_recent = AsyncMock(return_value=[test_signal])

    # mock find_by_config_id
    mock_repo.find_by_config_id = AsyncMock(return_value=([test_signal], 1))

    return mock_repo, test_signal


def create_test_app(config_repo: AsyncMock, signal_repo: AsyncMock):
    """创建带有mock依赖的测试应用"""
    from fastapi import FastAPI
    from src.api.strategy import router as strategy_router
    from src.api.strategy import get_config_repo, get_signal_repo

    test_app = FastAPI()

    # 设置依赖覆盖
    test_app.dependency_overrides[get_config_repo] = lambda: config_repo
    test_app.dependency_overrides[get_signal_repo] = lambda: signal_repo

    # 注册路由
    test_app.include_router(strategy_router)

    return test_app


# ==================== 策略配置 CRUD 测试 ====================


class TestStrategyAPI:
    """策略配置 API 测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试环境"""
        # 创建 mock 仓储
        self.config_repo, self.test_config_id, self.test_config_dict = create_mock_config_repo()
        self.signal_repo, self.test_signal = create_mock_signal_repo()

        yield

    @pytest.mark.asyncio
    async def test_get_strategies_success(self):
        """测试获取所有策略配置 - 成功"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/strategies")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_get_strategies_with_pagination(self):
        """测试获取策略配置 - 分页参数"""
        # 设置分页返回值
        self.config_repo.get_all = AsyncMock(return_value=([], 0))

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/strategies?page=2&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    @pytest.mark.asyncio
    async def test_get_strategies_with_enabled_filter(self):
        """测试获取策略配置 - 按启用状态过滤"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/strategies?is_enabled=true")

        assert response.status_code == 200
        # 验证传递给仓储的参数
        self.config_repo.find_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_strategy_success(self):
        """测试创建策略配置 - 成功"""
        new_strategy_data = {
            "name": "new_strategy",
            "description": "New strategy",
            "trigger_type": "each_kline_close",
            "macd_params": {"fast1": 12, "slow1": 26, "signal1": 9},
            "threshold": 0.0,
            "symbol": "BINANCE:ETHUSDT",
            "interval": "15",
            "is_enabled": True,
        }

        # 修改 mock，使 find_by_id 返回创建后的数据
        created_id = uuid4()
        created_config = {
            "id": created_id,
            "name": new_strategy_data["name"],
            "description": new_strategy_data["description"],
            "trigger_type": new_strategy_data["trigger_type"],
            "macd_params": new_strategy_data["macd_params"],
            "threshold": new_strategy_data["threshold"],
            "symbol": new_strategy_data["symbol"],
            "interval": new_strategy_data["interval"],
            "is_enabled": new_strategy_data["is_enabled"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "created_by": "test",
        }
        self.config_repo.create = AsyncMock(return_value=created_id)
        self.config_repo.find_by_id = AsyncMock(return_value=created_config)

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.post("/api/v1/strategies", json=new_strategy_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == new_strategy_data["name"]
        assert data["symbol"] == new_strategy_data["symbol"]

    @pytest.mark.asyncio
    async def test_create_strategy_missing_required_field(self):
        """测试创建策略配置 - 缺少必填字段"""
        # 缺少必填字段 name 和 symbol
        incomplete_data = {
            "description": "Incomplete strategy",
            "interval": "60",
        }

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.post("/api/v1/strategies", json=incomplete_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_strategy_by_id_success(self):
        """测试获取单个策略配置 - 成功"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get(f"/api/v1/strategies/{self.test_config_id}")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data

    @pytest.mark.asyncio
    async def test_get_strategy_by_id_not_found(self):
        """测试获取单个策略配置 - 404不存在"""
        # 设置为返回 None
        self.config_repo.find_by_id = AsyncMock(return_value=None)

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get(f"/api/v1/strategies/{uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_strategy_by_id_invalid_uuid(self):
        """测试获取单个策略配置 - 无效UUID"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/strategies/invalid-uuid")

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_update_strategy_success(self):
        """测试更新策略配置 - 成功"""
        update_data = {
            "name": "updated_strategy",
            "description": "Updated description",
        }

        # 修改 mock，使 find_by_id 返回更新后的数据
        updated_config = self.test_config_dict.copy()
        updated_config["name"] = update_data["name"]
        updated_config["description"] = update_data["description"]
        self.config_repo.find_by_id = AsyncMock(return_value=updated_config)

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.put(
            f"/api/v1/strategies/{self.test_config_id}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]

    @pytest.mark.asyncio
    async def test_update_strategy_not_found(self):
        """测试更新策略配置 - 404不存在"""
        self.config_repo.find_by_id = AsyncMock(return_value=None)

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.put(
            f"/api/v1/strategies/{uuid4()}",
            json={"name": "updated"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_strategy_success(self):
        """测试删除策略配置 - 成功"""
        self.config_repo.delete = AsyncMock(return_value=True)

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.delete(f"/api/v1/strategies/{self.test_config_id}")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_strategy_not_found(self):
        """测试删除策略配置 - 404不存在"""
        self.config_repo.delete = AsyncMock(return_value=False)

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.delete(f"/api/v1/strategies/{uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_enable_strategy_success(self):
        """测试启用策略 - 成功"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.patch(f"/api/v1/strategies/{self.test_config_id}/enable")

        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is True
        assert "message" in data

    @pytest.mark.asyncio
    async def test_enable_strategy_not_found(self):
        """测试启用策略 - 404不存在"""
        self.config_repo.find_by_id = AsyncMock(return_value=None)

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.patch(f"/api/v1/strategies/{uuid4()}/enable")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_disable_strategy_success(self):
        """测试禁用策略 - 成功"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.patch(f"/api/v1/strategies/{self.test_config_id}/disable")

        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False

    @pytest.mark.asyncio
    async def test_disable_strategy_not_found(self):
        """测试禁用策略 - 404不存在"""
        self.config_repo.find_by_id = AsyncMock(return_value=None)

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.patch(f"/api/v1/strategies/{uuid4()}/disable")

        assert response.status_code == 404


# ==================== 信号查询测试 ====================


class TestSignalAPI:
    """信号查询 API 测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试环境"""
        self.config_repo, _, _ = create_mock_config_repo()
        self.signal_repo, self.test_signal = create_mock_signal_repo()

        yield

    @pytest.mark.asyncio
    async def test_get_signals_success(self):
        """测试获取信号列表 - 成功"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/signals")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_get_signals_with_filters(self):
        """测试获取信号列表 - 带过滤条件"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get(
            "/api/v1/signals?"
            "symbol=BINANCE:BTCUSDT&"
            "strategy_name=test_strategy&"
            "interval=60&"
            "signal_value=true"
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_signals_pagination(self):
        """测试获取信号列表 - 分页"""
        self.signal_repo.find_all = AsyncMock(return_value=([], 0))

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/signals?page=3&page_size=50")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 3
        assert data["page_size"] == 50

    @pytest.mark.asyncio
    async def test_get_signals_page_size_limit(self):
        """测试获取信号列表 - page_size 边界值"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        # page_size 超过最大值 100
        response = client.get("/api/v1/signals?page_size=200")

        # FastAPI 会自动验证并返回 422
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_signal_by_id_success(self):
        """测试获取单个信号 - 成功"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/signals/1")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "signal_id" in data

    @pytest.mark.asyncio
    async def test_get_signal_by_id_not_found(self):
        """测试获取单个信号 - 404不存在"""
        self.signal_repo.find_by_id = AsyncMock(return_value=None)

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/signals/999999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_recent_signals_success(self):
        """测试获取最近信号 - 成功"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/signals/recent")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_recent_signals_with_limit(self):
        """测试获取最近信号 - 带 limit 参数"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/signals/recent?limit=5")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_signals_by_config_success(self):
        """测试获取指定策略的信号 - 成功"""
        config_id = uuid4()

        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get(f"/api/v1/signals/strategy/{config_id}")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_signals_by_config_invalid_uuid(self):
        """测试获取指定策略的信号 - 无效UUID"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/signals/strategy/invalid-uuid")

        assert response.status_code == 400


# ==================== 错误响应测试 ====================


class TestErrorResponses:
    """错误响应测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试环境"""
        self.config_repo, _, _ = create_mock_config_repo()
        self.signal_repo, _ = create_mock_signal_repo()

        yield

    @pytest.mark.asyncio
    async def test_repository_not_initialized(self):
        """测试仓储未初始化 - 500错误"""
        from fastapi import FastAPI
        from src.api.strategy import router as strategy_router
        from src.api.strategy import get_config_repo

        # 创建一个不使用依赖覆盖的应用
        test_app = FastAPI()
        test_app.include_router(strategy_router)

        client = TestClient(test_app)
        response = client.get("/api/v1/strategies")

        # 应该返回 500 因为仓储未初始化
        assert response.status_code == 500


# ==================== 参数验证测试 ====================


class TestParameterValidation:
    """参数验证测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试环境"""
        self.config_repo, _, _ = create_mock_config_repo()
        self.signal_repo, _ = create_mock_signal_repo()

        yield

    @pytest.mark.asyncio
    async def test_pagination_page_zero_invalid(self):
        """测试分页 - page=0 无效"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/strategies?page=0")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_pagination_page_negative_invalid(self):
        """测试分页 - page 负数无效"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/strategies?page=-1")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_pagination_page_size_zero_invalid(self):
        """测试分页 - page_size=0 无效"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/strategies?page_size=0")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_recent_signals_limit_too_high(self):
        """测试最近信号 - limit 超过最大值"""
        app = create_test_app(self.config_repo, self.signal_repo)
        client = TestClient(app)
        response = client.get("/api/v1/signals/recent?limit=200")

        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
