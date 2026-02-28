"""输出 Writer 基类"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseWriter(ABC):
    @abstractmethod
    def write(self, df: pd.DataFrame, output_config: dict) -> None:
        """将 DataFrame 写出到目标位置"""
        ...
