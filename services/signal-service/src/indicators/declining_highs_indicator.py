import numpy as np
import pandas as pd

from .indicator_cache import IndicatorCache


class DecliningHighsIndicator:
    """
    检测高点越来越低的趋跌状态且收盘价高于最近枢轴高点的技术指标
    """

    def __init__(self):
        self.cache = IndicatorCache()

    def calculate_indicators(
        self,
        price_series: pd.Series,
        pivot_points: pd.Series,
        pivot_window_left: int = 5
    ) -> pd.Series:
        """
        检测是否处于高点越来越低的趋跌状态且收盘价格高于H1

        参数:
            price_series: 价格序列
            pivot_points: 枢轴点标记序列（高点）
            pivot_window_left: 枢轴点左窗口大小，用于避免未来数据

        返回:
            布尔数组，表示每个时间点是否处于高点越来越低且收盘价格高于H1的状态
        """
        params = {
            "pivot_window_left": pivot_window_left,
        }

        # 生成数据签名用于缓存
        data_signature = self._generate_data_signature(price_series, pivot_points)
        cache_key = self.cache.get_cache_key(
            self.__class__, params, data_signature
        )

        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        n = len(price_series)
        result = np.zeros(n, dtype=bool)

        for i in range(n):
            # 获取当前位置之前的枢轴高点
            prev_pivots = []
            pivot_prices = []  # 记录枢轴点的价格

            # 从右向左查找最近的两个枢轴高点，避免使用未来数据
            start_idx = i - pivot_window_left  # 确保不使用未来数据
            for j in range(start_idx, 0, -1):
                if pivot_points.iloc[j]:
                    prev_pivots.append(j)  # 记录索引
                    pivot_prices.append(price_series.iloc[j])  # 记录价格
                    if len(prev_pivots) == 2:
                        break

            # 如果找到了两个枢轴高点，比较它们的大小
            if len(prev_pivots) == 2:
                h1, h2 = pivot_prices[0], pivot_prices[1]  # h1是更近的高点
                if (
                    h1 < h2 and h1 < price_series.iloc[i]
                ):  # 高点越来越低的状态（更近的高点低于更远的高点,且开仓价格高于h1
                    result[i] = True

        result_series = pd.Series(result, index=price_series.index)
        self.cache.set(cache_key, result_series)

        return result_series

    def _generate_data_signature(self, price_series: pd.Series, pivot_points: pd.Series) -> str:
        """
        生成数据签名，用于缓存标识

        参数:
            price_series: 价格序列
            pivot_points: 枢轴点序列

        返回:
            str: 数据签名字符串
        """
        # 获取第一个和最后一个价格值
        first_price = price_series.iloc[0]
        last_price = price_series.iloc[-1]

        # 获取第一个和最后一个枢轴点值
        first_pivot = pivot_points.iloc[0]
        last_pivot = pivot_points.iloc[-1]

        # 获取第一个和最后一个时间索引
        first_time = str(price_series.index[0])
        last_time = str(price_series.index[-1])

        # 组合成签名字符串
        data_signature = (
            f"{first_price:.6f}_{last_price:.6f}_"
            f"{first_pivot}_{last_pivot}_"
            f"{first_time}_{last_time}"
        )

        return data_signature
