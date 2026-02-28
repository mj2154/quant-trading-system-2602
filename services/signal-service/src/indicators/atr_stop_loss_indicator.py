import logging
from datetime import datetime

import numpy as np
import pandas as pd
import talib as ta

from .indicator_cache import IndicatorCache


class ATRStopLossIndicator:
    logger = logging.getLogger(__name__)

    def __init__(
        self,
    ):
        self.cache = IndicatorCache()
        self.ATR = ta.ATR
        self.MIN = ta.MIN
        self.MAX = ta.MAX

    def calculate_indicators(
        self,
        close: pd.Series,
        high: pd.Series,
        low: pd.Series,
        atr_length: int,
        atr_lookback: int,
        stop_size: float,
        use_atr_multiplier: bool,
    ) -> pd.DataFrame:
        params = {
            "atr_length": atr_length,
            "atr_lookback": atr_lookback,
            "stop_size": stop_size,
            "use_atr_multiplier": use_atr_multiplier,
        }
        # 构建带索引的DataFrame
        df = pd.DataFrame(
            {"close": close, "high": high, "low": low},
            index=close.index,  # 显式继承索引
        )

        data_signature = self.generate_data_signature(close, high, low)
        cache_key = self.cache.get_cache_key(
            self.__class__, params, data_signature
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        self.logger.debug(f"[{self.__class__.__name__}] 缓存未命中，开始计算指标...")

        # 计算ATR（结果转换为Series并保留索引）
        atr = self.ATR(
            high=high.to_numpy(dtype=np.float64),
            low=low.to_numpy(dtype=np.float64),
            close=close.to_numpy(dtype=np.float64),
            timeperiod=params["atr_length"],
        )
        atrname = f"atr_{params['atr_length']}"
        df[atrname] = pd.Series(atr, index=df.index)  # 索引对齐

        # 计算滚动极值（结果转换为Series）
        lookback = params["atr_lookback"]
        lowest = pd.Series(
            self.MIN(low.to_numpy(), lookback),
            index=df.index,  # 关键：继承原始索引
        )
        highest = pd.Series(
            self.MAX(high.to_numpy(), lookback),
            index=df.index,  # 关键：继承原始索引
        )

        # 动态止损（自动广播）
        adjusted_stop = (
            df[atrname] * params["stop_size"]
            if use_atr_multiplier
            else params["stop_size"]
        )

        # 向量化计算（索引自动对齐）
        df["long_size"] = df["close"] - lowest + adjusted_stop
        df["short_size"] = highest - df["close"] + adjusted_stop

        result = df[[atrname, "long_size", "short_size"]]

        self.cache.set(cache_key, result)

        return result

    def generate_data_signature(self, close_series, high_series, low_series):
        """
        生成数据签名，用于缓存标识

        参数:
            close_series: 收盘价序列
            high_series: 最高价序列
            low_series: 最低价序列

        返回:
            str: 数据签名字符串
        """
        # 获取第一个和最后一个close值
        first_close = close_series.iloc[0]
        last_close = close_series.iloc[-1]

        # 获取第一个和最后一个high值
        first_high = high_series.iloc[0]
        last_high = high_series.iloc[-1]

        # 获取第一个和最后一个low值
        first_low = low_series.iloc[0]
        last_low = low_series.iloc[-1]

        # 获取第一个和最后一个时间索引
        first_time = str(close_series.index[0])
        last_time = str(close_series.index[-1])

        # 组合成签名字符串
        data_signature = (
            f"{first_close:.6f}_{last_close:.6f}_"
            f"{first_high:.6f}_{last_high:.6f}_"
            f"{first_low:.6f}_{last_low:.6f}_"
            f"{first_time}_{last_time}"
        )

        return data_signature


if __name__ == "__main__":
    print("ATR Stop Loss Indicator")
    symbol = "BTCUSDT"
    interval = "1h"
    start = datetime(2025, 6, 1)
    end = datetime(2025, 6, 10)

    from data.binance_direct import BinanceDirectAPI
    api_client = BinanceDirectAPI()

    hist_data = api_client.fetch_klines(
        symbol=symbol, interval=interval, start_time=start, end_time=end
    )

    # 设置 time 为索引并排序
    hist_data.set_index("time", inplace=True)
    hist_data.sort_index(inplace=True)  # 确保按时间排序

    atr_loss = ATRStopLossIndicator()
    atr_loss_df = atr_loss.calculate_indicators(
        high=hist_data["high"],
        low=hist_data["low"],
        close=hist_data["close"],
        atr_length=16,
        atr_lookback=4,
        stop_size=1,
        use_atr_multiplier=True,
    )
    atr_loss_df = atr_loss.calculate_indicators(
        high=hist_data["high"],
        low=hist_data["low"],
        close=hist_data["close"],
        atr_length=16,
        atr_lookback=4,
        stop_size=1,
        use_atr_multiplier=True,
    )
    atr_loss_df = atr_loss.calculate_indicators(
        high=hist_data["high"],
        low=hist_data["low"],
        close=hist_data["close"],
        atr_length=16,
        atr_lookback=4,
        stop_size=1,
        use_atr_multiplier=True,
    )

    print(atr_loss.cache.get_stats())

    atr_loss_df1 = atr_loss.calculate_indicators(
        high=hist_data["high"],
        low=hist_data["low"],
        close=hist_data["close"],
        atr_length=12,
        atr_lookback=4,
        stop_size=1,
        use_atr_multiplier=True,
    )
    print(atr_loss.cache.get_stats())

    atr_loss_df1 = atr_loss.calculate_indicators(
        high=hist_data["high"],
        low=hist_data["low"],
        close=hist_data["close"],
        atr_length=14,
        atr_lookback=4,
        stop_size=1,
        use_atr_multiplier=True,
    )
    print(atr_loss.cache.get_stats())
