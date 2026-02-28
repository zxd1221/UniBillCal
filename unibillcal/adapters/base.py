"""数据源适配器基类"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseAdapter(ABC):
    """
    所有数据源适配器的抽象基类。
    子类只需实现 load() 方法，返回原始 DataFrame。
    """

    def __init__(self, source_config: dict):
        self.source_config = source_config

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """
        加载原始数据，返回 DataFrame。
        列名保持原始平台的列名，后续由 Mapper 处理。
        """
        ...

    def validate(self, df: pd.DataFrame, required_columns: list[str]) -> None:
        """验证 DataFrame 中是否包含必要列"""
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            raise ValueError(
                f"数据源缺少必要列: {missing}，"
                f"实际列: {list(df.columns)}"
            )
