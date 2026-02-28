import numpy as np
from numba import njit


@njit(cache=True)
def pivothigh(price: np.ndarray, left: int = 3, right: int = 3) -> np.ndarray:
    """向量化实现枢轴高点检测 (单列数据)，使用Numba JIT加速"""
    return _pivot_detection(price, left, right, mode='high')

@njit(cache=True)
def pivotlow(price: np.ndarray, left: int = 3, right: int = 3) -> np.ndarray:
    """向量化实现枢轴低点检测 (单列数据)，使用Numba JIT加速"""
    return _pivot_detection(price, left, right, mode='low')

@njit(cache=True)
def _pivot_detection(price: np.ndarray, left: int, right: int, mode: str) -> np.ndarray:
    """核心枢轴点检测逻辑 (JIT加速) - 单列数据版本"""
    n = len(price)
    window_size = left + right + 1
    result = np.zeros(n, dtype=np.bool_)

    # 如果数据长度不足以形成窗口，直接返回全False
    if n < window_size:
        return result

    # 遍历每个时间点 (从有效窗口开始位置到结束位置)
    for t in range(left, n - right):
        center_val = price[t]
        is_pivot = True

        # 检查左侧窗口
        for i in range(1, left + 1):
            if mode == 'high':
                if price[t - i] > center_val:
                    is_pivot = False
                    break
            else:  # mode == 'low'
                if price[t - i] < center_val:
                    is_pivot = False
                    break

        # 如果左侧已不符合条件，跳过右侧检查
        if not is_pivot:
            continue

        # 检查右侧窗口
        for i in range(1, right + 1):
            if mode == 'high':
                if price[t + i] > center_val:
                    is_pivot = False
                    break
            else:  # mode == 'low'
                if price[t + i] < center_val:
                    is_pivot = False
                    break

        # 设置结果
        result[t] = is_pivot

    return result
