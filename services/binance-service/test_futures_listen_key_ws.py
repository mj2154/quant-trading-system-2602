"""
测试期货 WS 私有数据客户端获取 listenKey

测试通过 WS 私有数据客户端的会话级认证方式获取 listenKey。
流程：
1. 连接 WebSocket (wss://testnet.binancefuture.com/ws-fapi/v1)
2. session.logon 会话级认证
3. 创建 listenKey

【重要】此测试必须在 Docker 容器中运行！

运行方式：
    docker exec -it binance-service /bin/bash
    cd /app
    uv run python test_futures_listen_key_ws.py
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
service_dir = Path(__file__).parent
sys.path.insert(0, str(service_dir / "src"))
sys.path.insert(0, str(service_dir))

# 加载.env文件
load_dotenv()

from clients.futures_private_ws_client import BinanceFuturesPrivateWSClient


def load_private_key(key_path: str) -> bytes:
    """加载PEM格式私钥"""
    with open(key_path, "rb") as f:
        return f.read()


async def test_futures_ws_listen_key():
    """测试期货 WS 客户端获取 listenKey"""

    print("=" * 60)
    print("测试期货 WS 私有数据客户端 - 获取 listenKey")
    print("=" * 60)

    # 获取 API 凭证
    api_key = os.environ.get("BINANCE_API_KEY")
    if not api_key:
        print("错误: 请设置 BINANCE_API_KEY 环境变量")
        return False

    # 私钥路径
    key_path = os.environ.get("BINANCE_FUTURES_PRIVATE_KEY_PATH")
    if not key_path:
        # 尝试默认路径
        key_path = service_dir / "keys" / "private_key.pem"
    else:
        key_path = Path(key_path)

    if not key_path.exists():
        print(f"错误: 私钥文件不存在: {key_path}")
        return False

    # 加载私钥
    private_key_pem = load_private_key(str(key_path))

    # 代理配置（Docker中使用 clash-proxy）
    proxy_url = os.environ.get("CLASH_PROXY_WS_URL", "http://clash-proxy:7890")

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"私钥: {key_path}")
    print(f"代理: {proxy_url}")
    print(f"WebSocket: wss://testnet.binancefuture.com/ws-fapi/v1")
    print("-" * 60)

    # 创建客户端
    client = BinanceFuturesPrivateWSClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        proxy_url=proxy_url,
        use_testnet=True,
    )

    try:
        # 1. 连接 WebSocket
        print("\n[1/4] 连接 WebSocket...")
        await client.connect()

        if not client._state.connected:
            print("  错误: 连接失败")
            return False
        print("  成功: WebSocket 已连接")

        # 2. session.logon 认证
        print("\n[2/4] 执行 session.logon 认证...")
        auth_success = await client._session_logon()

        if not auth_success:
            print("  错误: session.logon 认证失败")
            await client.disconnect()
            return False
        print("  成功: session.logon 认证通过")

        # 3. 创建 listenKey
        print("\n[3/4] 创建 listenKey...")
        listen_key = await client._create_listen_key()

        if not listen_key:
            print("  错误: listenKey 创建失败")
            await client.disconnect()
            return False
        print(f"  成功: listenKey = {listen_key}")

        # 4. 保持连接观察
        print("\n[4/4] 等待 10 秒观察数据流...")
        print("  (如果一切正常，应该会收到账户更新事件)")

        # 设置一个简单的回调来观察消息
        message_count = [0]

        async def on_message(package):
            message_count[0] += 1
            print(f"  收到消息 #{message_count[0]}: {package.data}")

        client.set_account_callback(on_message)

        # 等待 10 秒
        await asyncio.sleep(10)

        if message_count[0] > 0:
            print(f"\n  收到 {message_count[0]} 条消息，数据流正常!")
        else:
            print("\n  提示: 10 秒内未收到账户更新消息（可能没有挂单或持仓变化）")

        print("\n" + "=" * 60)
        print("✓ 测试通过! WS 客户端可以正常获取 listenKey")
        print("=" * 60)

        # 断开连接
        await client.disconnect()

        return True

    except Exception as e:
        print(f"\n异常: {e}")
        import traceback
        traceback.print_exc()

        try:
            await client.disconnect()
        except:
            pass

        return False


async def test_with_raw_message_debug():
    """带原始消息调试的测试"""

    print("=" * 60)
    print("调试测试 - 查看原始消息")
    print("=" * 60)

    api_key = os.environ.get("BINANCE_API_KEY")
    if not api_key:
        print("错误: 请设置 BINANCE_API_KEY")
        return False

    key_path = Path(os.environ.get("BINANCE_FUTURES_PRIVATE_KEY_PATH", "/app/keys/private_key.pem"))
    if not key_path.exists():
        print(f"错误: 私钥文件不存在: {key_path}")
        return False

    private_key_pem = load_private_key(str(key_path))
    proxy_url = os.environ.get("CLASH_PROXY_WS_URL", "http://clash-proxy:7890")

    client = BinanceFuturesPrivateWSClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        proxy_url=proxy_url,
        use_testnet=True,
    )

    try:
        print("\n[1] 连接 WebSocket...")
        await client.connect()
        print("  已连接")

        print("\n[2] session.logon 认证...")
        auth_success = await client._session_logon()
        print(f"  认证结果: {auth_success}")

        if not auth_success:
            return False

        print("\n[3] 发送 userDataStream.start 请求...")
        request_id = client._next_request_id()
        print(f"  请求 ID: {request_id}")

        # 直接发送请求并观察原始响应
        import json
        request = {
            "id": request_id,
            "method": "userDataStream.start",
            "params": {
                "apiKey": client.api_key,
            },
        }
        print(f"  发送请求: {json.dumps(request)}")

        await client._send(request)

        print("\n[4] 等待 15 秒观察所有收到的消息...")
        print("  (包括 listenKey 响应)")

        # 等待足够长的时间
        await asyncio.sleep(15)

        print(f"\n  listenKey 值: {client._listen_key}")

        if client._listen_key:
            print("\n✓ 测试通过!")
            return True
        else:
            print("\n✗ listenKey 未收到")
            return False

    except Exception as e:
        print(f"\n异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()


async def main():
    """主函数"""
    print("\n测试开始时间:", time.strftime("%Y-%m-%d %H:%M:%S"))

    # 先运行带调试的测试
    success = await test_with_raw_message_debug()

    print("\n测试结束时间:", time.strftime("%Y-%m-%d %H:%M:%S"))

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
