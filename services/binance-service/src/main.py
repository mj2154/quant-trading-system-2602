"""
币安服务主入口

通过环境变量配置：
- DATABASE_HOST: 数据库主机
- DATABASE_PORT: 数据库端口
- DATABASE_NAME: 数据库名称
- DATABASE_USER: 数据库用户
- DATABASE_PASSWORD: 数据库密码
- CLASH_PROXY_HTTP_URL: HTTP代理地址（可选）
- CLASH_PROXY_WS_URL: WebSocket代理地址（可选）
- LOG_LEVEL: 日志级别（默认INFO）
"""

import asyncio
import logging
import os
from urllib.parse import urlparse

from services import BinanceService

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_dsn() -> str:
    """构建数据库连接字符串"""
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "5432")
    name = os.getenv("DATABASE_NAME", "trading_db")
    user = os.getenv("DATABASE_USER", "dbuser")
    password = os.getenv("DATABASE_PASSWORD", "pass")

    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def main() -> None:
    """主入口"""
    logger.info("启动币安数据采集服务...")

    # 获取配置
    dsn = get_dsn()
    proxy_http = os.getenv("CLASH_PROXY_HTTP_URL")
    proxy_ws = os.getenv("CLASH_PROXY_WS_URL")

    logger.info(f"数据库: {urlparse(dsn).hostname}:{urlparse(dsn).port}")
    logger.info(f"HTTP代理: {proxy_http}")
    logger.info(f"WS代理: {proxy_ws}")

    # 创建并运行服务
    service = BinanceService(
        dsn=dsn,
        proxy_http=proxy_http,
        proxy_ws=proxy_ws,
    )

    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("收到中断信号")


if __name__ == "__main__":
    main()
