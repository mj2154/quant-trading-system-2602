#!/usr/bin/env python3
"""
验证脚本：使用MACD做空策略V1计算4小时BTCUSDT信号

用法：
    cd services/signal-service && uv run python verify_macd_short_v1.py
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timezone, timedelta

from src.db.database import Database
from src.strategies.macd_resonance_strategy import MACDResonanceShortStrategyV1

# 东8区时区
CST = timezone(timedelta(hours=8))


async def main():
    """主函数"""
    db = Database()
    await db.connect()

    # 获取最近300条已收盘的4小时K线数据
    # interval = '240' 代表4小时K线
    query = """
        SELECT
            open_time,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            close_time
        FROM klines_history
        WHERE symbol = 'BINANCE:BTCUSDT'
          AND interval = '240'
          AND close_time < NOW()
        ORDER BY open_time DESC
        LIMIT 500
    """

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query)

    if not rows:
        print("未找到4小时K线数据")
        await db.close()
        return

    print(f"获取到 {len(rows)} 条4小时K线数据")

    # 转换数据格式（按时间正序排列）
    data = []
    for row in rows:
        open_time = row["open_time"]
        if hasattr(open_time, "timestamp"):
            time_ms = int(open_time.timestamp() * 1000)
        else:
            time_ms = open_time

        data.append({
            "time": time_ms,
            "open": float(row["open_price"]) if row["open_price"] else None,
            "high": float(row["high_price"]) if row["high_price"] else None,
            "low": float(row["low_price"]) if row["low_price"] else None,
            "close": float(row["close_price"]) if row["close_price"] else None,
            "volume": float(row["volume"]) if row["volume"] else None,
        })

    # 按时间正序排列
    data.reverse()
    df = pd.DataFrame(data).dropna()

    # 设置时间为索引（用于策略计算和信号匹配）
    df.set_index("time", inplace=True)

    print(f"有效数据 {len(df)} 条")
    print(f"时间范围 (东8区): {datetime.fromtimestamp(df.index[0] / 1000, tz=CST).strftime('%Y-%m-%d %H:%M')} ~ "
          f"{datetime.fromtimestamp(df.index[-1] / 1000, tz=CST).strftime('%Y-%m-%d %H:%M')}")

    # 使用MACD做空策略V1计算信号（告警ID: 2224bef7-d2e7-41e5-8990-b9056f88ab92）
    # 参数: macd1_fastperiod=18, macd1_slowperiod=19, macd2_fastperiod=21, macd2_slowperiod=34, macd1_signalperiod=35, macd2_signalperiod=17
    strategy = MACDResonanceShortStrategyV1()
    signals = strategy.generate_signals(
        df,
        macd1_fastperiod=18,
        macd1_slowperiod=19,
        macd1_signalperiod=35,
        macd2_fastperiod=21,
        macd2_slowperiod=34,
        macd2_signalperiod=17,
    )

    entries = signals.entries
    exits = signals.exits

    # 查找最后一个建仓信号
    last_entry_time_ms = None
    last_entry_params = None

    for col in entries.columns:
        for idx in entries.index:
            if entries.loc[idx, col] == 1:
                last_entry_time_ms = idx
                last_entry_params = col

    if last_entry_time_ms is not None:
        dt_cst = datetime.fromtimestamp(last_entry_time_ms / 1000, tz=CST)
        close_price = df.loc[last_entry_time_ms, "close"]
        open_price = df.loc[last_entry_time_ms, "open"]
        high_price = df.loc[last_entry_time_ms, "high"]
        low_price = df.loc[last_entry_time_ms, "low"]

        print("\n" + "=" * 60)
        print("最后一个建仓信号（做空）:")
        print("=" * 60)
        print(f"  时间 (东8区): {dt_cst.strftime('%Y-%m-%d %H:%M')}")
        print(f"  K线数据:")
        print(f"    开盘价: {open_price}")
        print(f"    最高价: {high_price}")
        print(f"    最低价: {low_price}")
        print(f"    收盘价: {close_price}")
        print(f"  策略参数:")
        print(f"    macd1_fastperiod: {last_entry_params[0]}")
        print(f"    macd1_slowperiod: {last_entry_params[1]}")
        print(f"    macd1_signalperiod: {last_entry_params[2]}")
        print(f"    macd2_fastperiod: {last_entry_params[3]}")
        print(f"    macd2_slowperiod: {last_entry_params[4]}")
        print(f"    macd2_signalperiod: {last_entry_params[5]}")
        print("=" * 60)

        # 打印该信号之后的出场信号
        print("\n该建仓信号之后的出场信号:")
        exit_found = False
        for exit_col in exits.columns:
            for exit_idx in exits.index:
                if exit_idx > last_entry_time_ms and exits.loc[exit_idx, exit_col] == 1:
                    exit_dt_cst = datetime.fromtimestamp(exit_idx / 1000, tz=CST)
                    exit_close = df.loc[exit_idx, "close"]
                    print(f"  出场时间: {exit_dt_cst.strftime('%Y-%m-%d %H:%M')}, 收盘价: {exit_close}")
                    exit_found = True
                    break
            if exit_found:
                break

        if not exit_found:
            print("  暂无出场信号（持仓中）")
    else:
        print("\n未找到建仓信号")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
