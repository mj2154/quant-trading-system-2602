#!/usr/bin/env python3
"""直接测试 HTTP 客户端"""

import asyncio
import sys

# 添加路径
sys.path.insert(0, "/app/src")
sys.path.insert(0, "/app/shared/python")

from clients.spot_http_client import BinanceSpotHTTPClient
from clients.futures_http_client import BinanceFuturesHTTPClient


async def main():
    print("=" * 60)
    print("HTTP 客户端测试")
    print("=" * 60)

    # 现货客户端
    print("\n📦 现货客户端测试")
    spot = BinanceSpotHTTPClient(proxy_url="http://clash-proxy:7890")

    try:
        # 1. 测试交易所信息
        print("\n1. 获取交易所信息...")
        info = await spot.get_exchange_info()
        symbols = info.get("symbols", [])
        print(f"   ✅ 成功获取 {len(symbols)} 个交易对")
        if symbols:
            print(f"   示例: {symbols[0]['symbol']}")

        # 2. 测试 K 线
        print("\n2. 获取 K 线数据 (BTCUSDT 1m)...")
        klines = await spot.get_klines("BTCUSDT", "1m", limit=5)
        print(f"   ✅ 成功获取 {klines.count} 条 K 线")
        if klines.bars:
            latest = klines.bars[-1]
            print(f"   最新: {latest.close:.2f} @ {latest.time}")

        # 3. 测试 24hr Ticker
        print("\n3. 获取 24hr Ticker...")
        ticker = await spot.get_24hr_ticker("BTCUSDT")
        print(f"   ✅ 成功获取: {ticker.v.get('lp', 'N/A')}")

    except Exception as e:
        print(f"   ❌ 现货客户端错误: {e}")

    finally:
        await spot.close()

    # 期货客户端
    print("\n\n📦 期货客户端测试")
    futures = BinanceFuturesHTTPClient(proxy_url="http://clash-proxy:7890")

    try:
        # 1. 测试连续合约 K 线
        print("\n1. 获取连续合约 K 线 (BTCUSDT PERPETUAL 1m)...")
        klines = await futures.get_continuous_klines("BTCUSDT", "PERPETUAL", "1m", limit=5)
        print(f"   ✅ 成功获取 {klines.count} 条 K 线")
        if klines.bars:
            latest = klines.bars[-1]
            print(f"   最新: {latest.close:.2f} @ {latest.time}")

        # 2. 测试 24hr Ticker
        print("\n2. 获取期货 24hr Ticker...")
        ticker = await futures.get_24hr_ticker("BTCUSDT")
        print(f"   ✅ 成功获取: {ticker.v.get('lp', 'N/A')}")

    except Exception as e:
        print(f"   ❌ 期货客户端错误: {e}")

    finally:
        await futures.close()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
