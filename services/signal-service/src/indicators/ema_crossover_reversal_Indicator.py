import numpy as np
import pandas as pd

from .indicator_cache import IndicatorCache


class EMACrossoverReversalIndicator:
    """
    EMA交叉信号指标：当N根K线上穿EMA线，而N+1根K线下穿EMA线时发出信号
    """

    def __init__(self):
        self.cache = IndicatorCache()

    def calculate_indicators(self, close: pd.Series, ema: pd.Series) -> pd.Series:
        """
        检测N根K线上穿EMA线，而N+1根K线下穿EMA线的信号

        参数:
            close: 收盘价序列
            ema: EMA指标序列

        返回:
            布尔数组，表示每个时间点是否满足N上穿EMA而N+1下穿EMA的条件
        """
        params = {}

        # 生成数据签名用于缓存
        data_signature = self._generate_data_signature(close, ema)
        cache_key = self.cache.get_cache_key(self.__class__, params, data_signature)

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # 初始化结果数组
        n = len(close)
        result = np.zeros(n, dtype=bool)

        # 计算上穿和下穿信号
        # 上穿条件：当前收盘价 > EMA 且 前一个收盘价 <= EMA
        crossover = (close > ema) & (close.shift(1) <= ema.shift(1))
        # 下穿条件：当前收盘价 < EMA 且 前一个收盘价 >= EMA
        crossunder = (close < ema) & (close.shift(1) >= ema.shift(1))

        # 寻找满足条件的信号：N根K线上穿EMA，N+1根K线下穿EMA
        # 即在位置i处上穿，位置i+1处下穿
        for i in range(n - 1):  # 确保不会越界
            if crossover.iloc[i] and crossunder.iloc[i + 1]:
                result[i + 1] = True #将下穿的K线位置设置为True

        result_series = pd.Series(result, index=close.index)
        self.cache.set(cache_key, result_series)

        return result_series

    def _generate_data_signature(self, close: pd.Series, ema: pd.Series) -> str:
        """
        生成数据签名，用于缓存标识

        参数:
            close: 收盘价序列
            ema: EMA序列

        返回:
            str: 数据签名字符串
        """
        # 获取第一个和最后一个价格值
        first_close = close.iloc[0]
        last_close = close.iloc[-1]

        # 获取第一个和最后一个EMA值
        first_ema = ema.iloc[0]
        last_ema = ema.iloc[-1]

        # 获取第一个和最后一个时间索引
        first_time = str(close.index[0])
        last_time = str(close.index[-1])

        # 组合成签名字符串
        data_signature = (
            f"{first_close:.6f}_{last_close:.6f}_"
            f"{first_ema:.6f}_{last_ema:.6f}_"
            f"{first_time}_{last_time}"
        )

        return data_signature
