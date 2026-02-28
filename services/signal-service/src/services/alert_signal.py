"""AlertSignal - 策略配置 + 策略实例的封装

将告警配置和策略实例封装在一起，作为信号服务的核心数据单元。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import pandas as pd

from ..strategies.base import Strategy, StrategyOutput
from .trigger_engine import TriggerState

# 策略计算所需的最少K线数量
REQUIRED_KLINES = 280


@dataclass
class AlertSignal:
    """告警信号实例 - 策略配置 + 策略实例的封装

    将告警配置和策略实例封装在一起，作为信号服务的核心数据单元。
    这样设计的好处：
    1. 单一数据源：避免在多个 dict 中维护状态
    2. 简化更新逻辑：配置变更时直接删除重建
    3. 代码简洁：查找策略时直接通过 alert_id 获取
    """

    # 配置信息（来自 alert_configs 表）
    alert_id: UUID
    name: str
    strategy_type: str  # 策略类型，如 "MACDResonanceStrategyV5"
    symbol: str  # 交易对，如 "BINANCE:BTCUSDT"
    interval: str  # K线周期，如 "60"
    trigger_type: str  # 触发类型
    params: dict[str, Any]  # 策略参数（单一参数组合，非数组）
    is_enabled: bool  # 是否启用

    # 运行时状态
    strategy: Strategy  # 策略实例
    trigger_state: TriggerState  # 触发器状态
    created_at: datetime  # 创建时间
    updated_at: datetime  # 更新时间

    def calculate(self, ohlcv: pd.DataFrame) -> StrategyOutput:
        """计算实时信号

        将K线数据传入策略的 generate_signals 方法，
        从返回的信号矩阵中提取最后一根K线对应的信号。

        Args:
            ohlcv: K线数据 DataFrame，至少需要 280 根K线

        Returns:
            StrategyOutput: 包含 signal_value 和 signal_reason
        """
        # 调用策略的批量信号生成（前端已确保传入单一参数组合）
        signals = self.strategy.generate_signals(
            ohlcv=ohlcv,
            **self.params
        )

        # 提取最后一个信号（对应最后一根K线）
        # 前端已限制参数为单一组合，columns 只有一列
        last_entry = signals.entries.iloc[-1, 0]  # 入场信号 (0 或 1)
        last_exit = signals.exits.iloc[-1, 0]  # 出场信号 (0 或 1)

        # 决定信号值：出场信号优先，其次入场信号
        if last_exit == 1:
            return StrategyOutput(signal_value=False, signal_reason="清仓信号")
        elif last_entry == 1:
            return StrategyOutput(signal_value=True, signal_reason="建仓信号")
        else:
            return StrategyOutput(signal_value=None, signal_reason="无信号")
