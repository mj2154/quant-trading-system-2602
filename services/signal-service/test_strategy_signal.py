#!/usr/bin/env python3
"""
测试脚本：验证MACDResonanceShortStrategyV1策略原生计算结果

用法：
    cd services/signal-service && uv run python test_strategy_signal.py
"""

import asyncio
import sys
import os
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timezone, timedelta


async def main():
    """主函数"""
    from src.db.database import Database
    from src.strategies.macd_resonance_strategy import MACDResonanceShortStrategyV1
    from src.indicators import MACDIndicator, EMAIndicator

    db = Database()
    await db.connect()

    # 获取最近1000条1分钟K线数据
    query = """
        SELECT open_time, open_price, high_price, low_price, close_price, volume
        FROM klines_history
        WHERE symbol = 'BINANCE:BTCUSDT' AND interval = '1'
        ORDER BY open_time DESC
        LIMIT 1000
    """

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query)

    if not rows:
        print("未找到K线数据")
        return

    # 转换数据格式
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

    data.reverse()
    df = pd.DataFrame(data).dropna()

    # 计算MACD指标
    params = {
        "macd1_fastperiod": 18,
        "macd1_slowperiod": 19,
        "macd2_fastperiod": 21,
        "macd2_slowperiod": 34,
        "macd1_signalperiod": 35,
        "macd2_signalperiod": 17,
    }

    macd_ind = MACDIndicator()

    macd1 = macd_ind.calculate_indicators(df["close"], params["macd1_fastperiod"], params["macd1_slowperiod"], params["macd1_signalperiod"])
    macd2 = macd_ind.calculate_indicators(df["close"], params["macd2_fastperiod"], params["macd2_slowperiod"], params["macd2_signalperiod"])

    macd1_line = macd1["macd"]
    macd1_signal = macd1["macd_signal"]
    macd2_line = macd2["macd"]
    macd2_signal = macd2["macd_signal"]

    # 计算死叉和金叉（与策略代码一致）
    macd1_bearish_cross = (macd1_line < macd1_signal) & (macd1_line.shift(1) >= macd1_signal.shift(1))
    macd2_bearish_cross = (macd2_line < macd2_signal) & (macd2_line.shift(1) >= macd2_signal.shift(1))
    entries_raw = (macd1_bearish_cross & macd2_bearish_cross)

    macd2_golden_cross = (macd2_line > macd2_signal) & (macd2_line.shift(1) <= macd2_signal.shift(1))

    # EMA
    ema_ind = EMAIndicator()
    ema48 = ema_ind.calculate_indicators(df["close"], 48)["ema"]
    ema96 = ema_ind.calculate_indicators(df["close"], 96)["ema"]
    ema192 = ema_ind.calculate_indicators(df["close"], 192)["ema"]

    # 特定空头状态
    特定空头状态 = (ema96 < ema192) & (ema48 < ema192)

    # 价格下穿EMA
    price_cross_below_ema48 = (df["close"] < ema48) & (df["close"].shift(1) >= ema48.shift(1))
    price_cross_below_ema96 = (df["close"] < ema96) & (df["close"].shift(1) >= ema96.shift(1))
    price_cross_below_ema192 = (df["close"] < ema192) & (df["close"].shift(1) >= ema192.shift(1))
    cross_below_any_ema = price_cross_below_ema48 | price_cross_below_ema96 | price_cross_below_ema192

    # 打印21:25-21:40的详细MACD状态
    print("时间        close    死叉1   死叉2   原始入场  空头状态  下穿EMA  filterCond  最终入场  金叉2  出场")
    for i in range(len(df)):
        kline_time = df.iloc[i]["time"]
        dt = datetime.fromtimestamp(kline_time / 1000, tz=timezone.utc)
        cst = dt.astimezone(timezone(timedelta(hours=8)))
        if cst.hour >= 21 and cst.hour < 22 and cst.minute >= 25 and cst.minute <= 40:
            close = df.iloc[i]["close"]

            # 原始入场信号
            raw_entry = 1 if entries_raw.iloc[i] else 0

            # 过滤条件
            bear = 特定空头状态.iloc[i]
            cross = cross_below_any_ema.iloc[i]
            filter_cond = bear and not cross

            # 最终入场 = 原始入场 AND NOT filter_cond
            final_entry = 1 if (raw_entry and not filter_cond) else 0

            # 出场
            exit_sig = 1 if macd2_golden_cross.iloc[i] else 0

            dc1 = "X" if macd1_bearish_cross.iloc[i] else " "
            dc2 = "X" if macd2_bearish_cross.iloc[i] else " "
            gc2 = "X" if macd2_golden_cross.iloc[i] else " "

            print(f"{cst.strftime('%H:%M')}  {close:8.2f}   {dc1}      {dc2}       {raw_entry}        {'X' if bear else ' '}       {'X' if cross else ' '}       {'X' if filter_cond else ' '}        {final_entry}       {gc2}     {exit_sig}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
