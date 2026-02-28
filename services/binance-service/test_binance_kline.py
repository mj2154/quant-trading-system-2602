#!/usr/bin/env python
"""
测试币安服务获取K线功能
"""
import asyncio
import json
import time
from datetime import datetime

import httpx
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 配置
PROXY_URL = "http://clash-proxy:7890"
BINANCE_API = "https://api.binance.com/api/v3/klines"

# 测试时间范围（2026-02-06 10:00 - 23:00，对齐到小时）
FROM_TIME = 1770321600000  # 2026-02-06 10:00:00
TO_TIME = 1770372000000    # 2026-02-06 23:00:00


def get_interval_ms(resolution: str) -> int:
    """分辨率到毫秒的转换"""
    if resolution.endswith("m"):
        return int(resolution[:-1]) * 60 * 1000
    elif resolution.endswith("h"):
        return int(resolution[:-1]) * 60 * 60 * 1000
    elif resolution.endswith("d"):
        return int(resolution[:-1]) * 24 * 60 * 60 * 1000
    else:
        return int(resolution) * 60 * 1000


async def fetch_klines_from_binance(symbol: str, interval: str, start_time: int, end_time: int) -> list:
    """从币安API获取K线数据"""
    interval_ms = get_interval_ms(interval)

    klines = []
    current_start = start_time

    async with httpx.AsyncClient(proxies=PROXY_URL, timeout=30.0) as client:
        while current_start < end_time:
            url = f"{BINANCE_API}?symbol={symbol}&interval={interval}&startTime={current_start}&limit=1000"

            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            for k in data:
                kline_time = k[0]  # open_time in milliseconds
                if kline_time > end_time:
                    return klines
                klines.append({
                    "time": kline_time,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })

            current_start = klines[-1]["time"] + interval_ms
            print(f"  获取到 {len(klines)} 条数据，最新时间: {datetime.fromtimestamp(klines[-1]['time']/1000)}")

    return klines


async def test_binance_fetch():
    """测试币安API获取K线"""
    print("=" * 60)
    print("测试币安API获取K线数据")
    print("=" * 60)

    symbol = "BTCUSDT"
    interval = "1h"

    print(f"\n请求参数:")
    print(f"  交易对: {symbol}")
    print(f"  间隔: {interval}")
    print(f"  开始时间: {datetime.fromtimestamp(FROM_TIME/1000)} ({FROM_TIME})")
    print(f"  结束时间: {datetime.fromtimestamp(TO_TIME/1000)} ({TO_TIME})")

    print(f"\n开始从币安API获取数据...")
    klines = await fetch_klines_from_binance(symbol, interval, FROM_TIME, TO_TIME)

    print(f"\n✅ 成功获取 {len(klines)} 条K线数据")

    if klines:
        print(f"\n数据预览:")
        for k in klines[:5]:
            print(f"  {datetime.fromtimestamp(k['time']/1000)}: open={k['open']}, close={k['close']}")
        if len(klines) > 5:
            print(f"  ...")
            for k in klines[-3:]:
                print(f"  {datetime.fromtimestamp(k['time']/1000)}: open={k['open']}, close={k['close']}")

    return klines


async def main():
    """主函数"""
    try:
        klines = await test_binance_fetch()
        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
