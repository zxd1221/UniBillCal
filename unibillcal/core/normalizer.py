"""
BillNormalizer - 单平台账单标准化器

职责：将一个平台的原始数据转换为统一格式 DataFrame。
只做 ETL（抽取 → 过滤 → 字段映射），不做任何汇总或业务计算。

统一格式（Unified Schema）:
  date      | store  | order_id | amount | platform | remark | ...extra_fields
  ──────────┼────────┼──────────┼────────┼──────────┼────────┼───────────────
  2024-01-05│ 旗舰店A│ ALI001  │ 100.0  │ alipay   │        │

新增平台只需添加 YAML 配置文件，无需修改本类。
"""

from __future__ import annotations

import logging
import pandas as pd

from .config_loader import PlatformConfig
from .filter import apply_filter
from .mapper import FieldMapper
from ..adapters import get_adapter

logger = logging.getLogger(__name__)


class BillNormalizer:
    """
    将单个平台的原始账单标准化为统一格式。

    步骤：
      1. Load   - 通过适配器从数据源（Excel/SQL Server）读取原始数据
      2. Filter - 按配置过滤无效行（如只保留"交易成功"状态）
      3. Map    - 字段重命名 + 金额公式计算 → 统一列名

    用法:
        config = PlatformConfig.from_file("config/alipay.yaml")
        normalizer = BillNormalizer(config)
        unified_df = normalizer.normalize()
    """

    def __init__(self, config: PlatformConfig):
        self.config = config

    # ------------------------------------------------------------------ #
    #  主入口
    # ------------------------------------------------------------------ #

    def normalize(self, source_df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        执行标准化，返回统一格式 DataFrame。

        Args:
            source_df: 直接传入已加载的 DataFrame（跳过 Load 步骤），
                       主要用于单元测试。
        Returns:
            包含统一字段的 DataFrame（date/store/amount/platform 等）
        """
        platform = self.config.platform

        raw = source_df if source_df is not None else self._load()
        logger.info("[%s] 读取完成，共 %d 行", platform, len(raw))

        filtered = apply_filter(raw, self.config.filter)
        logger.info("[%s] 过滤后剩余 %d 行", platform, len(filtered))

        unified = FieldMapper(self.config).transform(filtered)
        logger.info("[%s] 标准化完成，统一字段: %s", platform, list(unified.columns))

        return unified

    # ------------------------------------------------------------------ #
    #  分步方法（便于调试）
    # ------------------------------------------------------------------ #

    def load(self) -> pd.DataFrame:
        return self._load()

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        return apply_filter(df, self.config.filter)

    def map(self, df: pd.DataFrame) -> pd.DataFrame:
        return FieldMapper(self.config).transform(df)

    # ------------------------------------------------------------------ #
    #  内部
    # ------------------------------------------------------------------ #

    def _load(self) -> pd.DataFrame:
        src = self.config.source
        adapter_cls = get_adapter(src["type"])
        return adapter_cls(src).load()
