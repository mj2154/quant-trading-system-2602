import copy
import hashlib
import threading

import numpy as np
import pandas as pd
from cachetools import LRUCache


class IndicatorCache:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 确保只初始化一次
        if not hasattr(self, '_cache'):
            # 使用cachetools的LRUCache，最大缓存2000个项目
            self._cache = LRUCache(maxsize=2000)
            self._stats = {"hits": 0, "misses": 0}
            self._cache_lock = threading.RLock()

    @staticmethod
    def _hash_data(data) -> str:
        if isinstance(data, pd.DataFrame):
            # 增加时间范围哈希
            time_range_hash = hashlib.md5(
                f"{data.index[0]}_{data.index[-1]}".encode()
            ).hexdigest()[:8]

            # 对关键列采样（首尾各50行+最后100行）
            head = data[['open','high','low','close']].head(50)
            tail = data[['open','high','low','close']].tail(50)
            sample = pd.concat([head, tail]).to_numpy()

            return time_range_hash + hashlib.md5(sample.tobytes()).hexdigest()

        elif isinstance(data, pd.Series):
            # 时间序列增加起止点哈希
            if data.index.dtype == 'datetime64[ns]':
                range_hash = hashlib.md5(
                    f"{data.index[0]}_{data.index[-1]}".encode()
                ).hexdigest()[:8]
                return range_hash + hashlib.md5(data.tail(50).to_numpy().tobytes()).hexdigest()

            return hashlib.md5(data.tail(50).to_numpy().tobytes()).hexdigest()

        else:
            return hashlib.md5(np.asarray(data).tobytes()).hexdigest()

    def get_cache_key(self, indicator_cls, params: dict, data) -> str:
        """生成标准化的缓存键"""
        # 参数排序确保一致
        sorted_params = tuple(sorted(params.items()))
        data_hash = self._hash_data(data)
        key_tuple = (indicator_cls.__name__, sorted_params, data_hash)
        # 将元组转换为字符串作为缓存键
        return str(hash(key_tuple))

    def get(self, key):
        """线程安全的缓存获取"""
        with self._cache_lock:
            value = self._cache.get(key)
            if value is not None:
                self._stats["hits"] += 1
                # 返回深拷贝以避免修改缓存中的原始数据
                return copy.deepcopy(value)
            self._stats["misses"] += 1
            return None

    def set(self, key, value):
        """线程安全的缓存设置"""
        with self._cache_lock:
            # 由于使用了cachetools的LRUCache，它会自动处理大小限制和LRU淘汰策略
            self._cache[key] = copy.deepcopy(value)

    def get_stats(self):
        """获取缓存统计"""
        with self._cache_lock:
            return {
                "size": len(self._cache),
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "maxsize": self._cache.maxsize
            }

    def clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            self._cache.clear()
            self._stats = {"hits": 0, "misses": 0}
