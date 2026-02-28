"""
账户信息API测试

测试期货和现货账户信息请求的任务路由功能。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.gateway.task_router import TaskRouter


class TestAccountTaskRouter:
    """测试账户任务路由器"""

    @pytest.fixture
    def mock_subscription_manager(self):
        """创建模拟订阅管理器"""
        manager = MagicMock()
        manager.subscribe_batch = AsyncMock(return_value=1)
        manager.unsubscribe_batch = AsyncMock(return_value=1)
        manager.unsubscribe_all = AsyncMock(return_value=[])
        return manager

    @pytest.fixture
    def mock_client_manager(self):
        """创建模拟客户端管理器"""
        manager = MagicMock()
        manager.register_task = MagicMock()
        return manager

    @pytest.fixture
    def mock_tasks_repo(self):
        """创建模拟任务仓储"""
        repo = MagicMock()
        repo.create_task = AsyncMock(return_value="task-123")
        repo.get_pending_count = AsyncMock(return_value=0)
        return repo

    @pytest.fixture
    def router(self, mock_subscription_manager, mock_client_manager, mock_tasks_repo):
        """创建路由器实例"""
        router = TaskRouter(
            subscription_manager=mock_subscription_manager,
            client_manager=mock_client_manager,
            task_repo=None
        )
        router.set_tasks_repository(mock_tasks_repo)
        return router

    @pytest.mark.asyncio
    async def test_get_futures_account_creates_task(self, router, mock_tasks_repo):
        """测试获取期货账户信息创建异步任务"""
        # 构建请求
        request = {
            "action": "get",
            "data": {
                "type": "get_futures_account"
            },
            "requestId": "req-001"
        }

        # 执行
        response = await router.handle("client-001", request)

        # 验证任务被创建
        mock_tasks_repo.create_task.assert_called_once_with(
            task_type="get_futures_account",
            payload={"requestId": "req-001"}
        )

        # 验证返回 ack 确认
        assert response["action"] == "ack"
        assert response["requestId"] == "req-001"

    @pytest.mark.asyncio
    async def test_get_spot_account_creates_task(self, router, mock_tasks_repo):
        """测试获取现货账户信息创建异步任务"""
        # 构建请求
        request = {
            "action": "get",
            "data": {
                "type": "get_spot_account"
            },
            "requestId": "req-002"
        }

        # 执行
        response = await router.handle("client-001", request)

        # 验证任务被创建
        mock_tasks_repo.create_task.assert_called_once_with(
            task_type="get_spot_account",
            payload={"requestId": "req-002"}
        )

        # 验证返回 ack 确认
        assert response["action"] == "ack"
        assert response["requestId"] == "req-002"

    @pytest.mark.asyncio
    async def test_unknown_account_type_returns_error(self, router):
        """测试未知账户类型返回错误"""
        # 构建请求
        request = {
            "action": "get",
            "data": {
                "type": "get_unknown_account"
            },
            "requestId": "req-003"
        }

        # 执行
        response = await router.handle("client-001", request)

        # 验证返回错误
        assert response["action"] == "error"
        assert "errorCode" in response["data"]
        assert "UNKNOWN_REQUEST_TYPE" in response["data"]["errorCode"]

    @pytest.mark.asyncio
    async def test_tasks_repo_not_initialized_returns_error(self, mock_subscription_manager, mock_client_manager):
        """测试任务仓储未初始化时返回错误"""
        # 创建未设置任务仓储的路由器
        router = TaskRouter(
            subscription_manager=mock_subscription_manager,
            client_manager=mock_client_manager,
            task_repo=None
        )
        # 不设置 tasks_repo

        # 构建请求
        request = {
            "action": "get",
            "data": {
                "type": "get_futures_account"
            },
            "requestId": "req-004"
        }

        # 执行
        response = await router.handle("client-001", request)

        # 验证返回错误
        assert response["action"] == "error"
        assert "TASKS_REPOSITORY_NOT_SET" in response["data"]["errorCode"]
