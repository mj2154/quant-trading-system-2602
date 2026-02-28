import pandas as pd

from .indicator_cache import IndicatorCache


class PriceCrossoverEMAIndicator:
    """
    价格穿越EMA技术指标：检测价格穿越EMA线的信号（支持上穿和下穿）
    """

    def __init__(self):
        self.cache = IndicatorCache()

    def calculate_indicators(
        self,
        close: pd.Series,
        ema: pd.Series,
        mode: str = "crossover"
    ) -> pd.Series:
        """
        检测价格穿越EMA的信号

        参数:
            close: 收盘价序列
            ema: EMA指标序列
            mode: 穿越模式
                  "crossover" - 上穿EMA（默认）
                  "crossunder" - 下穿EMA

        返回:
            布尔数组，表示每个时间点是否出现价格穿越EMA的信号
        """
        # 验证模式参数
        if mode not in ["crossover", "crossunder"]:
            raise ValueError("mode参数必须是'crossover'或'crossunder'")

        params = {"mode": mode}

        # 生成数据签名用于缓存
        data_signature = self._generate_data_signature(close, ema, mode)
        cache_key = self.cache.get_cache_key(
            self.__class__, params, data_signature
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # 根据模式计算穿越信号
        if mode == "crossover":
            # 上穿条件：当前收盘价 > EMA 且 前一个收盘价 <= EMA
            cross_signal = (close > ema) & (close.shift(1) <= ema.shift(1))
        else:  # crossunder
            # 下穿条件：当前收盘价 < EMA 且 前一个收盘价 >= EMA
            cross_signal = (close < ema) & (close.shift(1) >= ema.shift(1))

        # 确保返回的是Series格式并保持索引一致
        result_series = pd.Series(cross_signal.values, index=close.index)
        self.cache.set(cache_key, result_series)

        return result_series

    def _generate_data_signature(self, close: pd.Series, ema: pd.Series, mode: str) -> str:
        """
        生成数据签名，用于缓存标识

        参数:
            close: 收盘价序列
            ema: EMA序列
            mode: 穿越模式

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
            f"{mode}_"
            f"{first_time}_{last_time}"
        )

        return data_signature
