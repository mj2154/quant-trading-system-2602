"""
账户数据流订阅验证脚本 v2

根据币安官方文档 (2026-02-04):
- 现货: listenKey REST API 已废弃，必须使用 WebSocket API + session.logon
- 期货: listenKey 方式仍然有效

验证步骤：
1. 现货: WebSocket API 认证 + userDataStream.subscribe
2. 期货: 传统的 listenKey 方式

运行方式:
    cd services/binance-service
    uv run python src/verify_user_stream.py --mode spot
    uv run python src/verify_user_stream.py --mode futures
    uv run python src/verify_user_stream.py --mode all
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# 添加项目路径
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir / "src"))
sys.path.insert(0, str(service_dir))

from dotenv import load_dotenv

from clients.spot_user_stream_client import SpotUserStreamClient
from clients.futures_user_stream_client import FuturesUserStreamClient
from clients.base_ws_client import WSDataPackage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


async def verify_futures_user_stream(timeout_seconds: int = 60) -> bool:
    """验证期货账户数据流（listenKey 方式，仍然有效）"""
    api_key = os.environ.get("BINANCE_API_KEY", "")
    private_key_path = os.environ.get(
        "BINANCE_FUTURES_PRIVATE_KEY_PATH",
        os.environ.get(
            "BINANCE_PRIVATE_KEY_PATH",
            str(service_dir / "keys" / "private_key.pem"),
        ),
    )
    proxy_url = os.environ.get("CLASH_PROXY_HTTP_URL")

    if not api_key:
        logger.error("BINANCE_API_KEY 环境变量未设置")
        return False

    if not Path(private_key_path).exists():
        logger.error(f"私钥文件不存在: {private_key_path}")
        return False

    private_key_pem = load_private_key(private_key_path)

    logger.info("=" * 50)
    logger.info("期货用户数据流验证 (listenKey 方式)")
    logger.info("=" * 50)
    logger.info(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    logger.info(f"WebSocket (Testnet): wss://fstream.binancefuture.com/ws/{{listenKey}}")
    logger.info(f"超时时间: {timeout_seconds}秒")
    logger.info("-" * 50)

    client = FuturesUserStreamClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        signature_type=os.environ.get("BINANCE_SIGNATURE_TYPE", "ed25519"),
        proxy_url=proxy_url,
    )

    received_events: list[dict] = []

    async def callback(package: WSDataPackage) -> None:
        # 从 WSDataPackage 中提取原始消息
        message = package.data
        event_type = message.get("e", "unknown")
        logger.info(f"[FUTURES] 收到事件: {event_type}")
        received_events.append(message)
        if len(received_events) >= 5:
            logger.info("已收到 5 个事件，停止接收")
            await client.stop()

    client.set_data_callback(callback)

    try:
        logger.info("启动期货用户数据流...")
        success = await client.start()

        if not success:
            logger.error("期货用户数据流启动失败")
            return False

        logger.info(f"等待账户事件（最多 {timeout_seconds} 秒）...")
        await asyncio.sleep(timeout_seconds)

        if client.is_connected:
            logger.info("仍在连接中，主动停止...")
            await client.stop()

    except Exception as e:
        logger.error(f"期货用户数据流异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    logger.info("-" * 50)
    logger.info(f"期货验证完成，共收到 {len(received_events)} 个事件")
    return len(received_events) > 0


async def verify_spot_user_stream_ws_api(timeout_seconds: int = 60) -> bool:
    """验证现货用户数据流 (WebSocket API 方式)

    根据币安官方文档 (2026-02-04):
    - 旧的 listenKey REST API 已废弃
    - 新方式: session.logon 认证 + userDataStream.subscribe
    """
    api_key = os.environ.get("BINANCE_API_KEY", "")
    private_key_path = os.environ.get(
        "BINANCE_PRIVATE_KEY_PATH",
        str(service_dir / "keys" / "private_key.pem"),
    )
    proxy_url = os.environ.get("CLASH_PROXY_HTTP_URL")

    if not api_key:
        logger.error("BINANCE_API_KEY 环境变量未设置")
        return False

    if not Path(private_key_path).exists():
        logger.error(f"私钥文件不存在: {private_key_path}")
        return False

    private_key_pem = load_private_key(private_key_path)

    # Demo Mode WebSocket API 端点
    # 根据文档，Demo Mode 现货应使用: wss://demo-ws-api.binance.com/ws-api/v3
    WS_API_URL = "wss://demo-ws-api.binance.com/ws-api/v3"

    logger.info("=" * 50)
    logger.info("现货用户数据流验证 (WebSocket API 方式)")
    logger.info("=" * 50)
    logger.info(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    logger.info(f"WebSocket API (Demo): {WS_API_URL}")
    logger.info(f"超时时间: {timeout_seconds}秒")
    logger.info("-" * 50)

    from utils.ed25519_signer import Ed25519Signer
    from websockets.asyncio.client import connect

    received_events: list[dict] = []
    request_id_counter = 1000

    def next_id() -> str:
        nonlocal request_id_counter
        req_id = str(request_id_counter)
        request_id_counter += 1
        return req_id

    try:
        connect_kwargs: dict[str, str] = {}
        if proxy_url:
            connect_kwargs["proxy"] = proxy_url

        logger.info("正在连接 WebSocket API...")
        async with connect(WS_API_URL, **connect_kwargs) as websocket:
            logger.info("WebSocket 连接已建立")

            # 步骤1: session.logon 认证
            logger.info("正在认证 (session.logon)...")
            timestamp = int(time.time() * 1000)

            auth_params = {
                "apiKey": api_key,
                "timestamp": timestamp,
            }
            sorted_params = dict(sorted(auth_params.items()))
            payload = "&".join(f"{k}={v}" for k, v in sorted_params.items())

            signer = Ed25519Signer(private_key_pem)
            signature = signer.sign(payload)

            auth_request = {
                "id": next_id(),
                "method": "session.logon",
                "params": {
                    "apiKey": api_key,
                    "timestamp": timestamp,
                    "signature": signature,
                },
            }

            await websocket.send(json.dumps(auth_request))
            logger.info(f"认证请求已发送: {auth_request['id']}")

            # 等待认证响应
            auth_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            auth_data = json.loads(auth_response)
            logger.info(f"认证响应: {auth_data}")

            if auth_data.get("status") != 200:
                logger.error(f"认证失败: {auth_data}")
                return False
            logger.info("认证成功!")

            # 步骤2: userDataStream.subscribe 订阅账户数据流
            # 注意：现货 WebSocket API 方式中，session.logon 后直接 subscribe，不需要 listenKey
            # 因为 session 已经关联了账户
            logger.info("正在订阅 (userDataStream.subscribe)...")
            subscribe_request = {
                "id": next_id(),
                "method": "userDataStream.subscribe",
                "params": {},
            }
            await websocket.send(json.dumps(subscribe_request))
            logger.info(f"订阅请求已发送")

            # 等待订阅确认
            sub_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            sub_data = json.loads(sub_response)
            logger.info(f"订阅响应: {sub_data}")

            if sub_data.get("status") != 200:
                logger.error(f"订阅失败: {sub_data}")
                return False

            logger.info("订阅成功，开始监听账户事件...")

            # 监听事件
            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)

                    # 现货 WebSocket API 事件格式：
                    # {"subscriptionId": 0, "event": {"e": "executionReport", ...}}
                    if "subscriptionId" in data and "event" in data:
                        event_data = data.get("event", {})
                        event_type = event_data.get("e", "unknown")
                        logger.info(f"[SPOT WS API] 收到事件: {event_type}")
                        received_events.append(event_data)

                        if len(received_events) >= 5:
                            logger.info("已收到 5 个事件，停止接收")
                            break

                except asyncio.TimeoutError:
                    continue

    except Exception as e:
        logger.error(f"WebSocket API 验证异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    logger.info("-" * 50)
    logger.info(f"现货验证完成，共收到 {len(received_events)} 个事件")

    if received_events:
        logger.info("事件详情:")
        for i, event in enumerate(received_events, 1):
            logger.info(f"  [{i}] {event.get('e', 'unknown')}")

    return len(received_events) > 0


async def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description="账户数据流订阅验证脚本 v2")
    parser.add_argument(
        "--mode",
        choices=["spot", "futures", "all"],
        default="all",
        help="验证模式: spot(现货), futures(期货), all(全部)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="每个客户端的最大运行时间（秒），默认60秒",
    )
    args = parser.parse_args()

    # 加载 .env 文件
    load_dotenv()

    results: dict[str, bool] = {}

    if args.mode in ("spot", "all"):
        results["spot"] = await verify_spot_user_stream_ws_api(args.timeout)

    if args.mode in ("futures", "all"):
        results["futures"] = await verify_futures_user_stream(args.timeout)

    # 打印总结
    logger.info("")
    logger.info("=" * 50)
    logger.info("验证结果总结")
    logger.info("=" * 50)
    for mode, success in results.items():
        status = "通过" if success else "失败"
        logger.info(f"  {mode}: {status}")
    logger.info("=" * 50)

    if all(results.values()):
        logger.info("所有验证通过！")
    else:
        logger.warning("部分验证失败")


if __name__ == "__main__":
    asyncio.run(main())
