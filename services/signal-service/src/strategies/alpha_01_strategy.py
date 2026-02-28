import numpy as np
import pandas as pd
from vectorbt.utils.params import create_param_product

from ..indicators import ATRStopLossIndicator, PivotHighLowIndicator
from .backtest_base import BaseStrategy, StrategyParam, StrategySignals
from .registry import StrategyMetadata, StrategyRegistry


class Alpha01Strategy(BaseStrategy):
    # Strategy metadata - must match class name exactly
    type: str = "Alpha01Strategy"
    name: str = "Alpha01策略"
    description: str = "基于ATR止损和枢轴点的趋势跟踪策略"
    params: list[StrategyParam] = []

    def __init__(self):
        super().__init__()
        self.atr_loss = ATRStopLossIndicator()
        self.pivot_point = PivotHighLowIndicator()

        # ... existing code ...

    def generate_signals(
        self,
        ohlcv: pd.DataFrame,
        atr_length: int | np.ndarray = 14,
        atr_lookback: int | np.ndarray = 1,
        atr_stop_size: float | np.ndarray = 1.0,
        use_atr_multiplier: bool | np.ndarray = True,
        pivot_window: int | np.ndarray = 3,
        need_param_product: bool = False,
    ) -> StrategySignals:
        # ... existing code ...
        # 参数标准化与维度展开
        params = {
            "atr_length": np.atleast_1d(atr_length),
            "atr_lookback": np.atleast_1d(atr_lookback),
            "atr_stop_size": np.atleast_1d(atr_stop_size),
            "use_atr_multiplier": np.atleast_1d(use_atr_multiplier),
            "pivot_window": np.atleast_1d(pivot_window),
        }
        param_list = [
            list(params["atr_length"]),
            list(params["atr_lookback"]),
            list(params["pivot_window"]),
            list(params["atr_stop_size"]),
            list(params["use_atr_multiplier"]),
        ]

        # 生成参数网格
        if need_param_product:
            param_product_list = create_param_product(param_list=param_list)
            param_count = len(param_product_list[0]) if param_product_list[0] else 0
        else:
            # 检查所有参数数组的长度是否一致
            param_lengths = [len(arr) for arr in param_list]
            if len(set(param_lengths)) > 1:
                raise ValueError(
                    f"当param_product=False时，所有参数数组的长度必须一致，当前长度为: {dict(zip(params.keys(), param_lengths))}"
                )

            # 如果所有参数数组长度一致，则直接使用
            param_product_list = param_list
            param_count = len(param_product_list[0]) if param_product_list[0] else 0

        # 预初始化信号矩阵
        close = ohlcv["close"]
        high = ohlcv["high"]
        low = ohlcv["low"]
        index = ohlcv.index
        signal_shape = (len(index), param_count)
        entries = np.zeros(signal_shape, dtype=np.int8)
        exits = np.zeros(signal_shape, dtype=np.int8)
        sl_data = np.zeros(signal_shape, dtype=np.float64)  # 止损价数组
        tp_data = np.zeros(signal_shape, dtype=np.float64)  # 止盈价数组

        # 批量计算信号
        for i in range(param_count):
            # 从param_product_list中提取参数
            # create_param_product返回的是转置的结构，每个子列表代表一个参数在所有组合中的值
            al = param_product_list[0][i]
            alb = param_product_list[1][i]
            asz = param_product_list[2][i]
            uam = param_product_list[3][i]
            pw = param_product_list[4][i]

            # 计算ATR指标
            atr_stop = self.atr_loss.calculate_indicators(
                close=close,
                high=high,
                low=low,
                atr_length=al,
                atr_lookback=alb,
                stop_size=asz,
                use_atr_multiplier=uam,
            )

            # 计算枢轴点
            pivot_lows = self.pivot_point.calculate_indicators(
                price_series=low,
                mode="low",
                left_bars=pw,
                right_bars=pw,
            )

            # 生成信号
            atr_long = atr_stop["long_size"].to_numpy()
            atr_short = atr_stop["short_size"].to_numpy()
            close_np = close.to_numpy()
            pivot_mask = pivot_lows.shift(pw).to_numpy().astype(bool)

            entries[:, i] = (pivot_mask & (atr_long > atr_short)).astype(np.int8)
            exits[:, i] = (atr_long <= atr_short).astype(np.int8)
            sl_data[:, i] = close_np - atr_long
            tp_data[:, i] = close + atr_long  # 多头止盈价

        # 创建多重索引列名
        # 重新构造参数组合的元组列表
        param_tuples = list(zip(*param_product_list))
        param_names = list(params.keys())
        columns = pd.MultiIndex.from_tuples(param_tuples, names=param_names)

        # 构建最终数据结构
        return StrategySignals(
            entries=pd.DataFrame(entries, index=index, columns=columns),
            exits=pd.DataFrame(exits, index=index, columns=columns),
            sl_data=pd.DataFrame(sl_data, index=index, columns=columns),
            tp_data=pd.DataFrame(tp_data, index=index, columns=columns),
        )


# ===========================================
# 策略注册
# ===========================================

# Alpha01策略参数
alpha_01_params = [
    StrategyParam(
        name="ema_period",
        type="int",
        default=50,
        min=1,
        max=500,
        description="EMA周期",
    ),
    StrategyParam(
        name="volume_ma_period",
        type="int",
        default=20,
        min=1,
        max=200,
        description="成交量MA周期",
    ),
    StrategyParam(
        name="threshold",
        type="float",
        default=0.02,
        min=0.0,
        max=1.0,
        description="阈值",
    ),
]

# 注册Alpha01策略
StrategyRegistry.register(
    StrategyMetadata(
        type="Alpha01Strategy",
        name="Alpha01策略",
        description="基于ATR止损和枢轴点的趋势跟踪策略",
        params=alpha_01_params,
    )
)
