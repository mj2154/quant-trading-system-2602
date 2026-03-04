#!/usr/bin/env python3
"""
测试币安私有WebSocket客户端认证
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加src目录到路径（支持本地和Docker环境）
SRC_PATH = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_PATH))

from clients.futures_private_ws_client import BinanceFuturesPrivateWSClient


async def test_futures_ws():
    """测试期货私有WS连接"""
    api_key = os.environ.get("BINANCE_API_KEY", "")
    private_key_path = os.environ.get("BINANCE_PRIVATE_KEY_PATH", str(SRC_PATH.parent / "keys" / "private_key.pem"))
    proxy_url = os.environ.get("CLASH_PROXY_WS_URL", "http://clash-proxy:7890")

    print(f"API Key: {api_key[:10]}..." if api_key else "API Key: 未设置")
    print(f"Private Key Path: {private_key_path}")
    print(f"Proxy URL: {proxy_url}")

    # 加载私钥
    try:
        with open(private_key_path, "rb") as f:
            private_key_pem = f.read()
        print("私钥加载成功")
    except FileNotFoundError:
        print(f"错误: 找不到私钥文件 {private_key_path}")
        return
    except Exception as e:
        print(f"错误: 加载私钥失败: {e}")
        return

    # 创建客户端
    client = BinanceFuturesPrivateWSClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        proxy_url=proxy_url,
        timeout=30.0,  # 增加超时时间
    )

    print("\n尝试连接...")
    try:
        await client.connect()
        print("连接成功!")

        # 等待认证结果
        print("等待认证...")
        await asyncio.sleep(5)

        if client.is_authenticated:
            print("认证成功!")

            # 尝试获取账户信息
            print("\n尝试获取账户信息...")
            try:
                account = await asyncio.wait_for(
                    client.get_account_info_v2(),
                    timeout=30.0
                )
                print(f"账户信息: {account}")
            except asyncio.TimeoutError:
                print("获取账户信息超时")
            except Exception as e:
                print(f"获取账户信息失败: {e}")
        else:
            print("认证失败!")

        await client.disconnect()
        print("已断开连接")

    except Exception as e:
        print(f"连接失败: {e}")
        import traceback
        traceback.print_exc()


async def test_spot_ws():
    """测试现货私有WS连接"""
    api_key = os.environ.get("BINANCE_API_KEY", "")
    private_key_path = os.environ.get("BINANCE_PRIVATE_KEY_PATH", str(SRC_PATH.parent / "keys" / "private_key.pem"))
    proxy_url = os.environ.get("CLASH_PROXY_WS_URL", "http://clash-proxy:7890")

    print(f"\n{'='*50}")
    print(f"API Key: {api_key[:10]}..." if api_key else "API Key: 未设置")
    print(f"Private Key Path: {private_key_path}")
    print(f"Proxy URL: {proxy_url}")

    # 加载私钥
    try:
        with open(private_key_path, "rb") as f:
            private_key_pem = f.read()
        print("私钥加载成功")
    except FileNotFoundError:
        print(f"错误: 找不到私钥文件 {private_key_path}")
        return
    except Exception as e:
        print(f"错误: 加载私钥失败: {e}")
        return

    # 使用现货WS客户端
    from clients.spot_private_ws_client import BinanceSpotPrivateWSClient

    client = BinanceSpotPrivateWSClient(
        api_key=api_key,
        private_key_pem=private_key_pem,
        proxy_url=proxy_url,
        timeout=30.0,
    )

    print("\n尝试连接现货WS...")
    try:
        await client.connect()
        print("连接成功!")

        # 等待认证
        print("等待认证...")
        await asyncio.sleep(5)

        if client.is_authenticated:
            print("认证成功!")

            # 尝试获取账户信息
            print("\n尝试获取账户信息...")
            try:
                account = await asyncio.wait_for(
                    client.get_account_info(),
                    timeout=30.0
                )
                print(f"账户信息: {account}")
            except asyncio.TimeoutError:
                print("获取账户信息超时")
            except Exception as e:
                print(f"获取账户信息失败: {e}")
        else:
            print("认证失败!")

        await client.disconnect()
        print("已断开连接")

    except Exception as e:
        print(f"连接失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    # 测试期货
    print("="*50)
    print("测试期货私有WebSocket")
    print("="*50)
    await test_futures_ws()

    # 测试现货
    await test_spot_ws()


if __name__ == "__main__":
    asyncio.run(main())
