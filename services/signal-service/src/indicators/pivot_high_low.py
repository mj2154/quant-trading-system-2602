import numpy as np
import pandas as pd

from .indicator_cache import IndicatorCache
from .pivot_point_np import pivothigh, pivotlow


class PivotHighLowIndicator:
    """
    枢轴点检测指标（优化版Pine Script pivothigh/pivotlow的Python实现）
    专为单列价格数据设计

    典型用法：
    >>> phi = PivotHighLowIndicator()
    >>> high_pivots = phi.detect_pivot_high(high_series)
    >>> low_pivots = phi.detect_pivot_low(low_series, left_bars=5)
    """

    def __init__(self):
        self.cache = IndicatorCache()

    def calculate_indicators(
        self,
        price_series: pd.Series,
        mode: str = "high",
        left_bars: int = 3,
        right_bars: int = 3,
    ) -> pd.Series:
        # 生成缓存键
        params = {"mode": mode, "left_bars": left_bars, "right_bars": right_bars}
        data_signature = self.generate_data_signature(price_series)
        cache_key = self.cache.get_cache_key(self.__class__, params, data_signature)

        # 尝试获取缓存
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # 缓存未命中，进行计算
        # 参数校验
        if min(left_bars, right_bars) < 1:
            raise ValueError("窗口参数必须大于等于1")

        # 转换为NumPy数组
        price_np = price_series.to_numpy().astype(np.float64)

        # 根据模式选择计算函数
        if mode == "high":
            result_array = pivothigh(price_np, left_bars, right_bars)
        elif mode == "low":
            result_array = pivotlow(price_np, left_bars, right_bars)
        else:
            raise ValueError(f"不支持的模式: {mode}")

        # 转换为 pandas Series，并复用原始索引
        result = pd.Series(result_array, index=price_series.index, name=f"{mode}_pivot")

        # 设置缓存
        self.cache.set(cache_key, result)

        return result

    def generate_data_signature(self, price_series):
        """
        生成数据签名，用于缓存标识

        参数:
            price_series: 价格序列

        返回:
            str: 数据签名字符串
        """
        # 获取第一个和最后一个价格值
        first_val = price_series.iloc[0]
        last_val = price_series.iloc[-1]

        # 获取第一个和最后一个时间索引
        first_time = str(price_series.index[0])
        last_time = str(price_series.index[-1])

        # 组合成签名字符串
        return f"{first_val:.6f}_{last_val:.6f}_{first_time}_{last_time}"
