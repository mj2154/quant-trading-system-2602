"""随机策略 - 用于测试数据流

⚠️ 注意：这是为了测试而设计的特殊策略
- 一定返回 True 或 False，不返回 None
- 仅用于验证数据流是否正常工作
- 生产环境请勿使用真实策略
"""

from typing import Any

import numpy as np
import pandas as pd

from .backtest_base import BaseStrategy, StrategySignals
from .registry import StrategyRegistry


class RandomStrategy(BaseStrategy):
    """随机策略 - 随机返回 True/False 信号用于测试

    ⚠️ 特殊设计（仅用于测试）：
    - 每次调用 generate_signals 时，一定返回入场或出场信号
    - 50% 概率返回入场信号 (True)
    - 50% 概率返回出场信号 (False)
    - 最后一根 K 线一定产生信号，不会返回 None
    - 用于验证整个数据流是否正常工作
    """

    type: str = "RandomStrategy"
    name: str = "随机策略(测试用)"
    description: str = "随机返回信号，用于测试数据流（不返回None）"
    params: list = []

    def __init__(self):
        super().__init__()

    def generate_signals(
        self,
        ohlcv: pd.DataFrame,
        seed: int | None = None,
        probability: float = 0.5,
        **kwargs: Any,  # 忽略未知参数（如 MACD 参数）
    ) -> StrategySignals:
        """生成随机信号

        ⚠️ 测试专用设计：
        - 最后一根 K 线（当前周期）一定返回信号
        - 不会返回 None，确保数据流测试正常

        Args:
            ohlcv: K线数据 (仅用于获取数据形状)
            seed: 随机种子，用于可重复测试
            probability: 返回 True 的概率 (默认 0.5)

        Returns:
            StrategySignals: 包含随机入场/出场信号（最后一根K线一定有信号）
        """
        # 设置随机种子
        if seed is not None:
            np.random.seed(seed)

        n = len(ohlcv)

        # 随机生成信号（历史K线）
        entries = np.random.random(n) < probability
        exits = np.random.random(n) < probability

        # ⚠️ 测试专用：确保最后一根K线一定返回信号（不做空也不做多）
        # 如果最后一个是 0（无信号），则强制设为 1
        # 这样确保一定会产生信号，便于测试数据流
        last_entry = True if np.random.random() < probability else False
        last_exit = True if np.random.random() < probability else False

        # 如果 entry 和 exit 都是 False，至少保证一个是 True
        if not last_entry and not last_exit:
            last_entry = True

        entries[-1] = last_entry
        exits[-1] = last_exit

        # 转换为 DataFrame
        entries_df = pd.DataFrame(entries.astype(np.int8), index=ohlcv.index)
        exits_df = pd.DataFrame(exits.astype(np.int8), index=ohlcv.index)

        return StrategySignals(
            entries=entries_df,
            exits=exits_df,
            sl_data=None,
            tp_data=None,
        )


# 注册策略
StrategyRegistry.register(RandomStrategy)
