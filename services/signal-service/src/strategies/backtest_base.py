# strategy/base_strategy.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class StrategySignals:
    entries: pd.DataFrame  # 入场信号表
    exits: pd.DataFrame  # 出场信号表
    sl_data: pd.DataFrame | None = None  # 止损信号表
    tp_data: pd.DataFrame | None = None # 止盈信号表


@dataclass
class StrategyParam:
    """Strategy parameter definition."""
    name: str
    type: str
    default: Any
    description: str = ""
    min: float | None = None
    max: float | None = None


class BaseStrategy(ABC):
    """Base class for all trading strategies.

    All strategy classes must declare the following class attributes:
    - type: str = "StrategyClassName" (must match class name)
    - name: str = "Strategy Display Name"
    - description: str = "Strategy description"
    - params: list[StrategyParam] = [...]
    """

    # Strategy metadata - must be declared in each subclass
    type: str = ""  # Strategy type identifier (class name)
    name: str = ""  # Strategy display name
    description: str = ""  # Strategy description
    params: list[StrategyParam] = field(default_factory=list)  # Strategy parameters

    @abstractmethod
    def generate_signals(
        self, ohlcv: pd.DataFrame, need_param_product: bool = False, *args, **kwargs
    ) -> StrategySignals:
        """
        接收原始K线数据DataFrame，返回带有交易信号列的DataFrame
        """
        pass
