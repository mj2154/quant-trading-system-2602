"""
API 网关服务主入口

轻量级 API 网关，支持:
- HTTP REST: /, /health (服务状态查询)
- WebSocket: /ws/market (客户端数据交互)
- 订阅管理: subscription_manager (realtime_data表机制)
- 任务管理: tasks表机制
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .gateway import (
    ClientManager,
    TaskRouter,
    DataProcessor,
    SubscriptionManager,
)
from .db.database import init_pool, close_pool, get_pool
from .db.tasks_repository import TasksRepository
from .db.strategy_signals_repository import StrategySignalsRepository
from .db.alert_signal_repository import AlertSignalRepository
from .models.db.task_models import UnifiedTaskPayload, TaskType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 全局组件实例
_client_manager: ClientManager | None = None
_task_router: TaskRouter | None = None
_subscription_manager: SubscriptionManager | None = None
_data_processor: DataProcessor | None = None
_tasks_repo: TasksRepository | None = None
_strategy_signals_repo: StrategySignalsRepository | None = None
_alert_repo: AlertSignalRepository | None = None


async def _create_initial_tasks(tasks_repo: TasksRepository) -> None:
    """创建启动时初始任务

    直接创建获取交易所信息任务，不检查历史任务状态。
    任务去重由业务逻辑处理（如 exchange_info 表已有数据可跳过写入）。
    """
    try:
        # 创建获取交易所信息任务
        task = UnifiedTaskPayload(
            action=TaskType.SYSTEM_FETCH_EXCHANGE_INFO,
            resource="BINANCE",
            params={"mode": "all"},
        )

        task_id = await tasks_repo.create_task(
            task_type=TaskType.SYSTEM_FETCH_EXCHANGE_INFO,
            payload={"action": task.action, "resource": task.resource, "params": task.params},
        )
        logger.info(f"初始任务已创建: {TaskType.SYSTEM_FETCH_EXCHANGE_INFO}, task_id={task_id}")

    except Exception as e:
        logger.error(f"创建初始任务失败: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理

    启动时初始化数据库连接、订阅管理器和通知监听器，
    关闭时清理资源。
    """
    global _client_manager, _task_router, _subscription_manager
    global _data_processor
    global _tasks_repo
    global _strategy_signals_repo, _alert_repo

    # 启动阶段
    logger.info("Starting API Gateway...")

    # 初始化数据库连接池
    await init_pool()
    logger.info("Database pool initialized")

    # 初始化组件
    pool = await get_pool()

    # 1. 初始化新任务仓储（基于 tasks 表）
    _tasks_repo = TasksRepository(pool)
    logger.info("TasksRepository initialized")

    # 1.1 初始化信号仓储（告警服务需要）
    _strategy_signals_repo = StrategySignalsRepository(pool)
    logger.info("StrategySignalsRepository initialized")

    # 1.2 初始化告警信号仓储
    _alert_repo = AlertSignalRepository(pool)
    logger.info("AlertSignalRepository initialized")

    # 2. 初始化交易所信息仓储
    from .db.exchange_info_repository import ExchangeInfoRepository
    _exchange_repo = ExchangeInfoRepository(pool)
    logger.info("ExchangeInfoRepository initialized")

    # 3. 初始化订阅管理器（必须在最前面，因为TaskRouter依赖它）
    _subscription_manager = SubscriptionManager(pool)
    await _subscription_manager.start()
    logger.info("SubscriptionManager initialized")

    # 3. 初始化ClientManager（必须在TaskRouter之前，因为TaskRouter依赖它）
    _client_manager = ClientManager()
    _client_manager.set_subscription_manager(_subscription_manager)
    logger.info("ClientManager initialized")

    # 4. 初始化TaskRouter（传入已初始化的client_manager）
    _task_router = TaskRouter(
        subscription_manager=_subscription_manager,
        client_manager=_client_manager,
    )
    # 设置新任务仓储
    _task_router.set_tasks_repository(_tasks_repo)
    # 设置交易所信息仓储
    _task_router.set_exchange_info_repository(_exchange_repo)
    # 设置告警仓储
    _task_router.set_alert_repository(_alert_repo, _strategy_signals_repo)
    logger.info("TaskRouter initialized")

    # 5. 启动时清空订阅表并发送clean通知
    # 因为重启后所有前端连接都断了
    await _subscription_manager.truncate_and_notify_clean()
    logger.info("Subscription table cleared on startup")

    # 6. 初始化统一数据处理中心 (DataProcessor)
    from .db.database import DATABASE_URL

    _data_processor = DataProcessor(
        dsn=DATABASE_URL,
        client_manager=_client_manager,
        tasks_repo=_tasks_repo,
    )
    await _data_processor.start()
    logger.info("DataProcessor started (unified data processing center)")

    # 9. 创建启动时初始任务
    await _create_initial_tasks(_tasks_repo)
    logger.info("Initial tasks created")

    logger.info("API Gateway started successfully")

    yield

    # 关闭阶段
    logger.info("Shutting down API Gateway...")

    # 1. 停止订阅管理器
    if _subscription_manager:
        await _subscription_manager.stop()

    # 2. 停止通知监听器 (统一数据处理中心)
    if _data_processor:
        await _data_processor.stop()

    # 3. 关闭数据库连接池
    await close_pool()
    logger.info("Database pool closed")

    logger.info("API Gateway shutdown complete")


# 创建 FastAPI 应用
app = FastAPI(
    title="API Gateway",
    description="量化交易系统 API 网关",
    version="1.0.0",
    lifespan=lifespan,
)

# 添加 CORS 中间件，允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== HTTP REST 端点 ==========


@app.get("/")
async def root() -> JSONResponse:
    """根路径 - 返回服务状态和版本信息

    Returns:
        服务信息 JSON 响应
    """
    return JSONResponse(
        content={
            "service": "API Gateway",
            "version": "1.0.0",
            "status": "running",
            "description": "量化交易系统统一入口",
        }
    )


@app.get("/health")
async def health() -> JSONResponse:
    """健康检查端点

    Returns:
        健康状态 JSON 响应
    """
    # 检查数据库连接
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    # 检查客户端连接
    client_count = _client_manager.get_client_count() if _client_manager else 0

    return JSONResponse(
        content={
            "status": "healthy" if db_status == "healthy" else "degraded",
            "components": {
                "database": db_status,
                "websocket": "healthy" if _client_manager else "not initialized",
            },
            "statistics": {
                "connected_clients": client_count,
            },
        }
    )


# ========== WebSocket 端点 ==========


@app.websocket("/ws/market")
async def ws_market(websocket: WebSocket) -> None:
    """WebSocket 端点 /ws/market

    客户端数据交互的主通道。

    Args:
        websocket: FastAPI WebSocket 连接
    """
    if _client_manager is None or _task_router is None:
        await websocket.close(code=1011)
        return

    # 获取客户端 IP
    client_host = (
        websocket.headers.get("X-Forwarded-For", "")
        or websocket.headers.get("X-Real-IP", "")
        or "unknown"
    )
    logger.info(f"WebSocket connection from {client_host}")

    try:
        # 使用 gateway 模块处理连接
        from .gateway import ws_market as handle_ws

        await handle_ws(
            websocket=websocket,
            client_manager=_client_manager,
            task_router=_task_router,
        )
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from {client_host}")
    except RuntimeError as e:
        # 处理 WebSocket 相关运行时错误（如 "WebSocket is not connected"）
        logger.debug(f"WebSocket runtime error (connection may be closed): {e}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        # 尝试安全关闭连接（可能已经关闭）
        try:
            await websocket.close(code=1011)
        except Exception:
            pass  # 连接已关闭，静默忽略


# ========== 启动入口 ==========


def main() -> None:
    """启动服务

    使用 uvicorn 作为 ASGI 服务器。
    """
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
