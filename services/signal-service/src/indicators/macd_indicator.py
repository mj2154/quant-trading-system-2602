import logging

import numpy as np
import pandas as pd
import talib as ta

from .indicator_cache import IndicatorCache


class MACDIndicator:
    logger = logging.getLogger(__name__)

    def __init__(
        self,
    ):
        self.cache = IndicatorCache()
        self.MACD = ta.MACD

    def calculate_indicators(
        self,
        close: pd.Series,
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9,
    ) -> pd.DataFrame:
        params = {
            "fastperiod": fastperiod,
            "slowperiod": slowperiod,
            "signalperiod": signalperiod,
        }

        data_signature = self.generate_data_signature(close)
        cache_key = self.cache.get_cache_key(
            self.__class__, params, data_signature
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        self.logger.debug(f"[{self.__class__.__name__}] 缓存未命中，开始计算指标...")

        # 使用ta.MACD计算MACD指标
        macd, macd_signal, macd_hist = self.MACD(
            close.to_numpy(dtype=np.float64),
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod
        )

        # 构建结果DataFrame，确保索引对齐
        result = pd.DataFrame(
            {
                "macd": pd.Series(macd, index=close.index),
                "macd_signal": pd.Series(macd_signal, index=close.index),
                "macd_hist": pd.Series(macd_hist, index=close.index),
            },
            index=close.index,
        )

        self.cache.set(cache_key, result)

        return result

    def generate_data_signature(self, close_series):
        """
        生成数据签名，用于缓存标识

        参数:
            close_series: 收盘价序列

        返回:
            str: 数据签名字符串
        """
        # 获取第一个和最后一个close值
        first_close = close_series.iloc[0]
        last_close = close_series.iloc[-1]

        # 获取第一个和最后一个时间索引
        first_time = str(close_series.index[0])
        last_time = str(close_series.index[-1])

        # 组合成签名字符串
        data_signature = (
            f"{first_close:.6f}_{last_close:.6f}_"
            f"{first_time}_{last_time}"
        )

        return data_signature
